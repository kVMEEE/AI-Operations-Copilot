"""Native-compatible fallback statistics; correlation differences documented in docs."""
import re, math, hashlib
from app.investigation.contracts import Evidence, Hypothesis, Findings

THRESHOLDS = {'cpu_usage':80.,'cpu_percent':80.,'memory_usage':85.,'memory_percent':85.,'latency_ms':1000.,'p99_latency_ms':1500.,'error_rate':.05,'disk_usage_percent':90.,'db_connections':100.,'network_drop_rate':.02}
RULES = [
 ('OOM Crash',r'OutOfMemoryError|oom-killer|out of memory|killed process.*memory','Critical'),
 ('Database Deadlock',r'Deadlock detected|deadlock.*transaction|lock wait timeout','High'),
 ('Database Connection Saturation',r'Connection pool exhausted|too many connections|database connection timeout|pool max_size reached','High'),
 ('Network Timeout',r'Connection timed out|ETIMEDOUT|upstream request timeout|gateway timeout|connection refused|network is unreachable','High'),
 ('Server Error 5xx',r'500 Internal Server Error|502 Bad Gateway|503 Service Unavailable|504 Gateway Timeout','High'),
 ('Disk Space Exhaustion',r'No space left on device|disk full|I/O error.*write','Critical'),
 ('Authentication & Security Failure',r'Authentication failed|Unauthorized 401|Forbidden 403|Invalid token','Medium'),
 ('Thread Pool Starvation',r'Thread pool exhausted|RejectedExecutionException|Thread starvation','High'),
 ('Slow Query Warning',r'Slow query:.*duration|query execution time >','Medium'),
 ('Application Exception',r'Exception in thread|Unhandled Exception|Traceback \(most recent call last\)|NullPointerException|Fatal error','High')]

def fallback(logs, metrics):
    patterns={}; errors=warnings=0
    for line in logs:
        match=next(((n,s) for n,r,s in RULES if re.search(r,line,re.I)),None)
        if not match and re.search('error|fatal',line,re.I): match=('Generic Error','Medium')
        if match:
            name,severity=match
            p=patterns.setdefault(name,dict(pattern=name,frequency=0,severity=severity,sample_lines=[])); p['frequency']+=1
            if len(p['sample_lines'])<3: p['sample_lines'].append(line)
            if severity in ('High','Critical') or name=='Generic Error': errors+=1
            else: warnings+=1
        elif 'warn' in line.lower(): warnings+=1
    anomalies=[]
    for name,raw in sorted(metrics.items()):
        vals=raw if isinstance(raw,list) else [raw]; mean=sum(vals)/len(vals)
        sd=math.sqrt(sum((x-mean)**2 for x in vals)/len(vals)); peak=max(vals)
        z=(peak-mean)/sd if sd>.0001 else 0
        threshold=THRESHOLDS.get(name,mean+2.5*sd)
        if threshold<=0: threshold=mean*1.5
        if peak>threshold or (len(vals)>3 and z>=2.5):
            ratio=peak/threshold if threshold>0 else 1
            severity='Critical' if ratio>=1.5 or z>=4 else 'High' if ratio>=1.1 or z>=2.5 else 'Medium'
            anomalies.append(dict(metric_name=name,value=vals[-1],peak_value=peak,threshold=threshold,z_score=z,severity=severity,description=f'Metric {name} exceeded its threshold or statistical baseline.'))
    lr=dict(patterns=sorted(patterns.values(),key=lambda p:-p['frequency']),total_logs=len(logs),error_count=errors,warning_count=warnings)
    mr=dict(anomalies=anomalies,total_metrics_evaluated=len(metrics),has_critical_anomaly=any(a['severity']=='Critical' for a in anomalies))
    names=' '.join(patterns); ms=' '.join(a['metric_name'] for a in anomalies)
    cat='Memory' if 'OOM' in names or ('memory' in ms and ('Server Error' in names or 'latency' in ms)) else 'Database' if 'Database' in names else 'Network' if 'Network' in names or ('network' in ms and ('latency' in ms or 'Server Error' in names)) else 'Disk' if 'Disk' in names or 'disk' in ms else 'CPU' if 'Thread' in names or 'cpu' in ms else 'Unknown' if errors or anomalies else 'None'
    return dict(logs=lr,metrics=mr,correlation=dict(primary_category=cat,cause=TITLES[cat],confidence_score=0,reasoning='Uncalibrated rule-based candidate; causal impact is not established.',contributing_factors=[]))

TITLES={'Database':'Database Saturation & Lock Contention','Memory':'Memory Exhaustion / OOM Symptoms','Network':'Network / Dependency Timeout','Disk':'Disk Pressure','CPU':'CPU / Thread Saturation','Unknown':'Insufficient Evidence for a Root Cause','None':'No Detected Anomalies'}

def collect(incident_id, incident, bridge):
    raw,engine=bridge.analyze_incident(incident.logs,incident.metrics)
    evidence=[]
    for i,p in enumerate(raw['logs']['patterns']):
        evidence.append(Evidence(id=f'{incident_id}:log:{i}',incident_id=incident_id,kind='log',source='logs:pattern:'+p['pattern'],values={'pattern':p['pattern'],'frequency':p['frequency'],'severity':p['severity'],'sample_line_indices':[j for j,line in enumerate(incident.logs) if line in p.get('sample_lines',[])]},excerpt='\n'.join(p.get('sample_lines',[]))[:1500]))
    anomalies={a['metric_name']:a for a in raw['metrics']['anomalies']}
    for name,values in sorted(incident.metrics.items()):
        vals=values if isinstance(values,list) else [values]; a=anomalies.get(name,{})
        evidence.append(Evidence(id=f'{incident_id}:metric:'+hashlib.sha256(name.encode()).hexdigest()[:12],incident_id=incident_id,kind='metric',source='metrics:'+name,values={'name':name,'peak':max(vals),'last':vals[-1],'samples':len(vals),'threshold':a.get('threshold',THRESHOLDS.get(name)),'anomaly':bool(a)}))
    hypotheses=[]
    needles={'Database':('Database','db_connections'),'Memory':('OOM','memory'),'Network':('Network','network'),'Disk':('Disk','disk'),'CPU':('Thread','cpu')}
    baseline=raw['correlation']['primary_category']
    for cat,terms in needles.items():
        supporting=[e.id for e in evidence if any(t.lower() in (e.source).lower() for t in terms) and (e.kind=='log' or e.values['anomaly'])]
        contradicting=[e.id for e in evidence if e.kind=='metric' and any(t.lower() in e.source.lower() for t in terms) and not e.values['anomaly']]
        if supporting:
            hypotheses.append(Hypothesis(category=cat,title=TITLES[cat],supporting=supporting,contradicting=contradicting,heuristic_score=raw['correlation'].get('confidence_score') if cat==baseline else None,uncertainty='high' if contradicting else 'moderate'))
    hypotheses.sort(key=lambda h:(h.category!=baseline,-len(h.supporting),h.category))
    if not hypotheses: hypotheses=[Hypothesis(category='None' if evidence and baseline=='None' else 'Unknown',title=TITLES['None' if evidence and baseline=='None' else 'Unknown'])]
    return Findings(engine=engine,**raw),evidence,hypotheses
