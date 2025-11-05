const uploadBtn = document.getElementById('uploadBtn');
const fileInput = document.getElementById('fileInput');
const askBtn = document.getElementById('askBtn');
const questionInput = document.getElementById('question');
const chatBox = document.getElementById('chatBox');

function pushMessage(role, text, sources=[]) {
  const wrap = document.createElement('div');
  wrap.className = 'msg';
  const r = document.createElement('div'); r.className='role'; r.textContent = role.toUpperCase();
  const b = document.createElement('div'); b.className='bubble'; b.textContent = text;
  wrap.appendChild(r); wrap.appendChild(b);
  if (sources && sources.length) {
    const ul = document.createElement('ul');
    sources.forEach(s => {
      const li = document.createElement('li');
      li.textContent = `[${s.index}] ${s.doc_name}: ${s.snippet}`;
      ul.appendChild(li);
    });
    wrap.appendChild(ul);
  }
  chatBox.appendChild(wrap);
  chatBox.scrollTop = chatBox.scrollHeight;
}

uploadBtn.onclick = async () => {
  if (!fileInput.files?.length) { alert("Pick at least one file"); return; }
  for (const f of fileInput.files) {
    const fd = new FormData();
    fd.append('file', f);
    fd.append('csrfmiddlewaretoken', getCSRF());
    pushMessage('system', `Uploading ${f.name}...`);
    const res = await fetch('/api/upload/', { method:'POST', body: fd });
    const data = await res.json();
    if (!data.ok) pushMessage('system', `Upload error: ${data.error || res.statusText}`);
    else pushMessage('system', `Embedded ${f.name} (${data.chunks} chunks).`);
  }
  fileInput.value = '';
};

askBtn.onclick = async () => {
  const q = questionInput.value.trim();
  if (!q) return;
  pushMessage('user', q);
  questionInput.value = '';
  const fd = new FormData();
  fd.append('question', q);
  fd.append('csrfmiddlewaretoken', getCSRF());
  const res = await fetch('/api/ask/', { method:'POST', body: fd });
  const data = await res.json();
  if (!data.ok) pushMessage('assistant', data.answer || 'Error');
  else pushMessage('assistant', data.answer, data.sources);
};

function getCSRF(){
  const n = 'csrftoken=';
  const c = document.cookie.split(';').find(x=>x.trim().startsWith(n));
  return c ? decodeURIComponent(c.split('=')[1]) : '';
}
