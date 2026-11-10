from datetime import datetime, timezone
from app.schemas.incident import ReportContent, RootCause, Recommendation, PostmortemArtifacts, LogAnalysisResult, MetricsAnalysisResult
from app.investigation.security import safe_html
from app.investigation.analytics import TITLES
from app.investigation.contracts import Citation, Hypothesis

# Diagnostic templates describe observations to inspect, never executed commands.
DIAGNOSTICS = {
    'Database': [
        ('Inspect contention and connection evidence', 'Compare the reported lock or connection-pool symptoms with available blocking-query and pool-occupancy records.', ('deadlock', 'blocking', 'pool', 'connection'), 'Read-only database monitoring access, if available; confirm which service owns the reported logs.', 'Reading existing monitoring adds little load. Avoid executing query plans with ANALYZE, cancelling queries, or changing pool limits.'),
        ('Correlate latency with contention', 'Compare latency samples with the timing of database errors; obtain aligned timestamps before attributing latency to contention.', ('timing', 'latency', 'contention'), 'Aligned log and metric timestamps; request them if they were not supplied.', 'Review existing records first. Live diagnostic queries may add load; coordinate with the operator.'),
    ],
    'Memory': [
        ('Inspect memory limits and OOM evidence', 'Compare OOM signatures with measured memory utilization and available allocation trends or configured limits.', ('memory', 'oom', 'allocation', 'limits'), 'Read access to the affected process or workload telemetry, if available; verify its identity from source records.', 'Existing telemetry review is read-only. Heap capture or profiling may pause workloads and expose secrets; neither is requested automatically.'),
        ('Resolve conflicting memory observations', 'Check whether normal and elevated memory observations cover the same process and time window; do not infer a crash solely from a threshold breach.', ('timing', 'memory'), 'Process identity and timestamps for each observation; request missing context.', 'No restart, heap dump, or memory-limit change is performed.'),
    ],
    'Network': [
        ('Distinguish timeout from connection refusal', 'Inspect the cited timeout signatures and any available dependency or DNS records to distinguish connection refusal, resolution failure and delayed responses.', ('timeout', 'refusal', 'dns', 'dependency'), 'Read access to existing dependency health and resolver records, if available; confirm the destination from evidence.', 'Review recorded observations first. Active probes generate traffic and require an operator-approved scope.'),
        ('Correlate latency and drop measurements', 'Compare available latency and network-drop samples with error timing; request missing measurements before identifying a failing dependency.', ('timing', 'latency', 'network'), 'Aligned metric and log timestamps; no topology is assumed.', 'No network configuration changes or unrestricted probes are executed.'),
    ],
    'Disk': [
        ('Inspect space and inode observations', 'Review the cited disk measurements or write-error signatures and obtain space and inode observations for the affected volume if available. A threshold breach does not establish 100% utilization.', ('disk', 'usage', 'inode', 'space'), 'Read-only storage monitoring and evidence identifying the affected volume; request missing identity.', 'Existing monitoring review is read-only. Recursive filesystem scans can add I/O; no scan or deletion is executed.'),
        ('Review retention and write-error timing', 'Compare existing retention information and write-error timing with the measured pressure before considering cleanup.', ('retention', 'deletion', 'disk'), 'Existing retention policy and aligned write-error timestamps, if available.', 'Deletion, rotation and retention changes require separate operator review and are not executed.'),
    ],
    'CPU': [
        ('Inspect CPU and queue observations', 'Compare measured CPU peaks with any available queue-depth and thread-rejection records; high CPU alone does not prove a queue backlog.', ('cpu', 'queue', 'thread'), 'Read access to CPU and queue telemetry for the same workload; request missing workload identity and timing.', 'Existing telemetry review is read-only. Profiling may add overhead and needs separate operator review.'),
        ('Check saturation timing', 'Determine whether thread rejection or latency observations coincide with the CPU samples before concluding a causal relationship.', ('timing', 'cpu', 'latency'), 'Aligned CPU, request and thread-pool timestamps where available.', 'No profiling, scaling or thread-pool configuration change is executed.'),
    ],
    'Unknown': [
        ('Collect discriminating telemetry', 'Obtain a bounded sample of error logs and relevant metric series, including normal observations, to distinguish candidate causes.', (), 'Operator-provided log and metric sources, with secrets redacted and timestamps retained when known.', 'Collect existing records first; do not run broad scans or enable verbose logging without impact review.'),
        ('Establish scope and timing', 'Request the affected workload identity, observation window and recent deployment context. Current evidence does not establish a supported root cause.', (), 'A confirmed incident time window and source ownership; these are missing context, not assumed facts.', 'No remediation is recommended or executed from insufficient evidence.'),
    ],
    'None': [
        ('Review coverage and thresholds', 'Compare the supplied normal observations with the reported incident window and check whether the measured signals cover the symptom. No detected anomaly is not proof of system health.', (), 'The symptom time window and expected metric baselines, if available.', 'Read-only review of existing telemetry; no configuration changes are executed.'),
    ],
}
CATEGORY_TERMS = {'Database': ('database', 'deadlock'), 'Memory': ('memory', 'oom'),
                  'Network': ('network', 'timeout'), 'Disk': ('disk', 'inode'), 'CPU': ('cpu', 'thread')}


def diagnostic_recommendations(selected, inv):
    by_id = {e.id: e for e in inv.evidence}
    refs = list(dict.fromkeys(selected.supporting + selected.contradicting))
    refs = [ref for ref in refs if ref in by_id]
    if selected.category in ('None', 'Unknown'):
        refs = [e.id for e in inv.evidence]
    recommendations = []
    for action, description, terms, prerequisite, impact in DIAGNOSTICS[selected.category]:
        citations = []
        for chunk in inv.chunks:
            text = (chunk.source + ' ' + chunk.heading + ' ' + chunk.content).lower()
            # Synthetic examples and unrelated context are not diagnostic authority.
            if 'synthetic' in chunk.heading.lower():
                continue
            if any(term in text for term in CATEGORY_TERMS.get(selected.category, ())):
                if any(term in chunk.content.lower() for term in terms):
                    citations.append(Citation(chunk_id=chunk.id, evidence_ids=refs[:30]))
        observations = []
        for ref in refs[:4]:
            evidence = by_id[ref]
            if evidence.kind == 'metric':
                observations.append(f"{evidence.values['name']}: observed peak {evidence.values['peak']}")
            else:
                observations.append(f"{evidence.values['pattern']}: {evidence.values['frequency']} classified log entries")
        if observations:
            description += ' Supplied observations: ' + '; '.join(observations) + '.'
        if not citations:
            description += ' No applicable retrieved runbook section is available; use these evidence-based checks as provisional guidance.'
        recommendations.append(Recommendation(
            action=action, description=description, is_safe=False, action_type='read_only',
            priority='High', evidence_ids=refs, citations=citations,
            prerequisites=[prerequisite], operational_impact=impact))
    return recommendations


def report(incident,inv):
    selected = inv.hypotheses[0]
    if inv.proposal is not None:
        if inv.verification.status != 'passed':
            raise ValueError('Cannot render an unverified proposal')
        proposal = inv.proposal
        if proposal.category == 'Unknown':
            selected = Hypothesis(category='Unknown', title=TITLES['Unknown'],
                                  supporting=proposal.supporting, contradicting=proposal.contradicting,
                                  missing=proposal.missing, uncertainty=proposal.uncertainty)
        else:
            selected = next(h for h in inv.hypotheses if h.category == proposal.category).model_copy(
                update={'supporting': proposal.supporting, 'contradicting': proposal.contradicting,
                        'missing': proposal.missing, 'uncertainty': proposal.uncertainty})
    cause=RootCause(cause=selected.title,confidence_score=selected.heuristic_score or 0,reasoning='Candidate based on the cited telemetry; causality and incident resolution are not established.',primary_category=selected.category,contributing_factors=selected.supporting,engine=inv.findings.engine)
    recommendations = diagnostic_recommendations(selected, inv)
    rows=['# Incident investigation', '', 'Analysis completed. No remediation was executed.', '', '## Modes',f'- Analytics: {inv.findings.engine}',f'- Retrieval: {inv.retrieval_mode}',f'- Provider: {inv.provider.active}',f'- Verification: {inv.verification.status}']
    if inv.verification.reasons:rows+=['- Fallback reason: '+r for r in inv.verification.reasons]
    rows+=['', '## Investigation conclusion', selected.title, '- Uncertainty: '+selected.uncertainty, '', '## Ranked baseline hypotheses']
    for h in inv.hypotheses:
        rows += [f'### {h.title}',f'- Uncertainty: {h.uncertainty}',f'- Supporting: {", ".join(h.supporting) or "none"}',f'- Contradicting: {", ".join(h.contradicting) or "none recorded"}', '- Missing: '+' '.join(h.missing)]
        if h.heuristic_score is not None:rows.append(f'- Heuristic baseline score: {h.heuristic_score} (not a probability)')
    rows+=['','## Authoritative metric observations','| Metric | Peak | Last | Threshold |','| --- | --- | --- | --- |']
    for e in inv.evidence:
        if e.kind=='metric': rows.append('| '+str(e.values['name']).replace('|','\\|')+' | '+str(e.values['peak'])+' | '+str(e.values['last'])+' | '+str(e.values['threshold'])+' |')
    if inv.proposal:
        rows += ['', '## Verified investigator selection', TITLES[inv.proposal.category],
                 '- Uncertainty: '+inv.proposal.uncertainty,
                 '- Supporting: '+', '.join(inv.proposal.supporting),
                 '- Contradicting: '+', '.join(inv.proposal.contradicting),
                 '- Missing: '+', '.join(inv.proposal.missing)]
        rows += ['- Citation: `'+c.chunk_id+'`' for c in inv.proposal.citations]
        rows += ['- Diagnostic: '+d.action+' ('+d.action_type+')' for d in inv.proposal.diagnostics]
    rows+=['','## Runbook context (untrusted operational documentation)']
    for c in inv.chunks:rows += [f'### {c.source} — {c.heading}',f'Chunk `{c.id}`, version `{c.version[:12]}`',c.content]
    rows += ['', '## Suggested diagnostics']
    for recommendation in recommendations:
        rows += ['### '+recommendation.action, recommendation.description,
                 '- Evidence: '+(', '.join(recommendation.evidence_ids) or 'No supplied evidence; collect missing telemetry.'),
                 '- Citations: '+(', '.join(c.chunk_id for c in recommendation.citations) or 'None applicable'),
                 '- Prerequisites: '+' '.join(recommendation.prerequisites),
                 '- Operational impact: '+recommendation.operational_impact]
    rows += ['', 'Citation validity establishes reference integrity, not semantic faithfulness.']
    summary='\n'.join(rows)
    return ReportContent(summary=summary,summary_html=safe_html(summary),root_cause=cause,recommendations=recommendations,generated_at=datetime.now(timezone.utc),engine_version=inv.findings.engine,artifacts=PostmortemArtifacts(logs_result=LogAnalysisResult(**inv.findings.logs),metrics_result=MetricsAnalysisResult(**inv.findings.metrics)),investigation=inv)
