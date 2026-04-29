async function postJson(url, payload){
  const r = await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  if(!r.ok){ throw new Error(await r.text()); }
  return r.json();
}

function fmtTime(s){ return s ? new Date(s).toLocaleTimeString() : ''; }

function renderPhones(sms){
  const buyerPhone = document.getElementById('buyer')?.value;
  const buyerEl = document.getElementById('buyer-chat');
  const merchantEl = document.getElementById('merchant-chat');
  if(!buyerEl || !merchantEl || !buyerPhone) return;

  const buyerMsgs = sms.filter(s => s.from_number === buyerPhone || s.to_number === buyerPhone);
  buyerEl.innerHTML = buyerMsgs.map(s => `<div class="bubble ${s.direction === 'inbound' ? 'out' : 'in'}">${s.body}<br><span class="small">${fmtTime(s.created_at)}</span></div>`).join('');

  const merchMsgs = sms.filter(s => s.from_number === '0799001100' || s.to_number === '0799001100');
  merchantEl.innerHTML = merchMsgs.map(s => `<div class="bubble ${s.direction === 'inbound' ? 'out' : 'in'}">${s.body}<br><span class="small">${fmtTime(s.created_at)}</span></div>`).join('');
}

async function refreshFeeds(){
  const [smsR, txR] = await Promise.all([fetch('/api/feed/sms'), fetch('/api/feed/transactions')]);
  const sms = await smsR.json(); const txs = await txR.json();
  const smsEl = document.getElementById('sms-history');
  if(smsEl){ smsEl.innerHTML = sms.map(s=>`<tr><td>${s.id}</td><td>${s.direction}</td><td>${s.body}</td><td>${fmtTime(s.created_at)}</td></tr>`).join(''); }
  const txEl = document.getElementById('txn-rows');
  if(txEl){ txEl.innerHTML = txs.map(t=>`<tr><td>${t.reference}</td><td>${t.type}</td><td>${t.amount} ${t.currency}</td><td><span class="badge sim">${t.status}</span></td><td>${fmtTime(t.created_at)}</td></tr>`).join(''); }
  renderPhones(sms);
}

function initMobile(){
  const sendBtn = document.getElementById('send-command');
  if(!sendBtn) return;
  sendBtn.onclick = async ()=>{
    const buyer = document.getElementById('buyer').value;
    const command = document.getElementById('command').value;
    const payload = {from_number: buyer, to_number:'DEMO-SWITCH', body: command};
    try { await postJson('/api/sms/inbound', payload); await refreshFeeds(); }
    catch(e){ alert('DEMO/SIMULATED error: '+e.message); }
  };
  document.getElementById('buyer').addEventListener('change', ()=>refreshFeeds().catch(()=>{}));
}

setInterval(()=>refreshFeeds().catch(()=>{}), 3000);
window.addEventListener('DOMContentLoaded', ()=>{ initMobile(); refreshFeeds().catch(()=>{}); });
