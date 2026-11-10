'use strict';
const $ = id => document.getElementById(id);
let current = null, timer = null;
async function api(path, options) {
  const response = await fetch(path, options);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === 'string' ? body.detail : `Request rejected (${response.status}); check input limits and numeric metrics.`);
  }
  return response.json();
}
function showError(error) { $('error').textContent = error.message; }
function cards(target, values, describe) {
  const parent = $(target); parent.replaceChildren();
  for (const value of values) {
    const card = document.createElement('pre'); card.style.whiteSpace = 'pre-wrap';
    card.textContent = describe(value); parent.append(card);
  }
}
async function history() {
  const jobs = await api('/api/v1/incidents/'); $('history').replaceChildren();
  for (const job of jobs) {
    const button = document.createElement('button');
    button.textContent = `${job.description} — ${job.status} — ${new Date(job.created_at).toLocaleString()}`;
    button.addEventListener('click', () => select(job.job_id)); $('history').append(button);
  }
}
async function select(id) {
  current = id; clearTimeout(timer); $('details').hidden = false;
  try { await poll(id); } catch (e) { showError(e); }
}
async function poll(id) {
  const job = await api(`/api/v1/incidents/${id}`); if (current !== id) return;
  $('job-title').textContent = job.description;
  $('status').textContent = `${job.status}: ${job.step}${job.error ? ' — '+job.error : ''}`;
  $('stages').textContent = JSON.stringify(await api(`/api/v1/incidents/${id}/stages`), null, 2);
  $('cancel').disabled = !['queued','processing'].includes(job.status);
  $('structured').textContent = JSON.stringify(job.result, null, 2);
  const inv = job.result?.investigation;
  $('report').replaceChildren();
  if (job.result) {
    // Only the server's allowlist-sanitized Markdown HTML enters this sink.
    $('report').innerHTML = job.result.summary_html;
  }
  $('modes').textContent = inv ? `Analytics: ${inv.findings.engine}; retrieval: ${inv.retrieval_mode}; provider: ${inv.provider.active}; verification: ${inv.verification.status}. ${inv.verification.reasons.join('; ')}` : 'Collecting evidence…';
  cards('hypotheses', inv?.hypotheses || [], h => JSON.stringify(h, null, 2));
  cards('evidence', inv?.evidence || [], e => JSON.stringify(e, null, 2));
  cards('citations', inv?.chunks || [], c => `${c.source} / ${c.heading}\nChunk: ${c.id}\nVersion: ${c.version}\n${c.content}`);
  $('trace').textContent = JSON.stringify(inv?.trace || [], null, 2);
  if (['queued','processing'].includes(job.status)) timer = setTimeout(() => poll(id).catch(showError), 400);
  else await history();
}
$('incident-form').addEventListener('submit', async event => {
  event.preventDefault(); $('submit').disabled = true; $('error').textContent = '';
  try {
    const job = await api('/api/v1/incidents/', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({description:$('description').value, logs:$('logs').value.split('\n').filter(Boolean),metrics:JSON.parse($('metrics').value || '{}'),mode:$('mode').value})});
    await select(job.job_id);
  } catch (e) { showError(e); } finally { $('submit').disabled = false; }
});
$('refresh').addEventListener('click', () => history().catch(showError));
$('cancel').addEventListener('click', async () => { try { await api(`/api/v1/incidents/${current}/cancel`,{method:'POST'}); await select(current); } catch(e) {showError(e);} });
api('/api/v1/engine/info').then(info => { $('engine').textContent = info.is_native ? 'Native C++ analytics' : 'Python fallback analytics'; }).catch(showError);
history().catch(showError);
