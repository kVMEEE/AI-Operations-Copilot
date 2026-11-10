from datetime import datetime, timezone
from app.schemas.incident import ReportContent, RootCause, Recommendation, PostmortemArtifacts, LogAnalysisResult, MetricsAnalysisResult
from app.investigation.security import safe_html
from app.investigation.analytics import TITLES

def report(incident,inv):
    selected=next((h for h in inv.hypotheses if inv.proposal and h.category==inv.proposal.category),inv.hypotheses[0])
    if inv.proposal and inv.proposal.category=='Unknown':
        from app.investigation.contracts import Hypothesis
        selected=Hypothesis(category='Unknown',title=TITLES['Unknown'])
    cause=RootCause(cause=selected.title,confidence_score=selected.heuristic_score or 0,reasoning='Candidate based on the cited telemetry; causality and incident resolution are not established.',primary_category=selected.category,contributing_factors=selected.supporting,engine=inv.findings.engine)
    recommendations=[Recommendation(action='Inspect supporting telemetry',description='Review cited evidence and obtain aligned timing, topology and deployment history before selecting remediation.',is_safe=False,priority='High',action_type='read_only')]
    rows=['# Incident investigation', '', 'Analysis completed. No remediation was executed.', '', '## Modes',f'- Analytics: {inv.findings.engine}',f'- Retrieval: {inv.retrieval_mode}',f'- Provider: {inv.provider.active}',f'- Verification: {inv.verification.status}']
    if inv.verification.reasons:rows+=['- Fallback reason: '+r for r in inv.verification.reasons]
    rows+=['','## Ranked hypotheses']
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
    rows+=['','## Suggested diagnostics','Inspect supporting telemetry and collect aligned timing. Diagnostic suggestions are not executed. Review operational impact before any active probes, profiling or configuration changes.','', 'Citation validity establishes reference integrity, not semantic faithfulness.']
    summary='\n'.join(rows)
    return ReportContent(summary=summary,summary_html=safe_html(summary),root_cause=cause,recommendations=recommendations,generated_at=datetime.now(timezone.utc),engine_version=inv.findings.engine,artifacts=PostmortemArtifacts(logs_result=LogAnalysisResult(**inv.findings.logs),metrics_result=MetricsAnalysisResult(**inv.findings.metrics)),investigation=inv)
