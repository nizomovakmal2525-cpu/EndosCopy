// Theme
function toggleTheme() {
  const html = document.documentElement;
  const dark = html.getAttribute('data-theme') === 'dark';
  html.setAttribute('data-theme', dark ? 'light' : 'dark');
  document.getElementById('iconSun').style.display  = dark ? 'none'  : 'block';
  document.getElementById('iconMoon').style.display = dark ? 'block' : 'none';
}

// File
function dragOver(e)  { e.preventDefault(); document.getElementById('uploadZone').classList.add('drag'); }
function dragLeave()  { document.getElementById('uploadZone').classList.remove('drag'); }
function dropFile(e)  { e.preventDefault(); dragLeave(); const f = e.dataTransfer.files[0]; if (f) loadFile(f); }
function fileChosen(e){ const f = e.target.files[0]; if (f) loadFile(f); }

function loadFile(file) {
  const reader = new FileReader();
  reader.onload = ev => {
    window._selectedFile = file;
    document.getElementById('previewImg').src = ev.target.result;
    document.getElementById('previewFname').textContent = file.name;
    const n = file.name.toLowerCase();
    document.getElementById('imgLabel').textContent =
      n.includes('colon') || n.includes('kolon') ? 'COLON' :
      n.includes('gastro') || n.includes('stomach') ? 'GASTRO' : 'ENDO';
    document.getElementById('uploadZone').style.display = 'none';
    document.getElementById('previewWrap').classList.add('show');
    document.getElementById('patientInfoWrap').classList.add('show');
    document.getElementById('analyzeBtn').disabled = false;
    
    // Show analyze button for new file
    document.querySelector('.analyze-cta-wrap').style.display = 'block';
    
    // Hide old results when loading new file
    ['progCard','resultsCard','recCard'].forEach(id => document.getElementById(id).classList.remove('show'));
    ['s1','s2','s3','s4','s5'].forEach(id => document.getElementById(id).className = 'step');
    document.getElementById('progFill').style.width = '0%';
    document.getElementById('progPct').textContent = '0%';
  };
  reader.readAsDataURL(file);
}

// On Load
document.addEventListener('DOMContentLoaded', () => {
  updateSidebarHistory();
});

async function updateSidebarHistory() {
  const sidebar = document.getElementById('sidebarHistory');
  if (!sidebar) return;
  
  try {
    const res = await fetch('/history');
    if (!res.ok) return;
    const data = await res.json();
    
    sidebar.innerHTML = '';
    data.slice(0, 5).forEach(item => {
      const div = document.createElement('div');
      div.className = 'hist-item';
      div.onclick = () => loadHistoryItem(item);
      div.innerHTML = `
        <div class="hist-thumb"><img src="${item.image_path}" style="width:100%; height:100%; object-fit:cover; border-radius:4px;"></div>
        <div class="hist-info">
          <div class="hist-name">${item.result.disease}</div>
          <div class="hist-date">${new Date(item.timestamp).toLocaleDateString()}</div>
        </div>
      `;
      sidebar.appendChild(div);
    });
  } catch (err) {
    console.error('Sidebar history error:', err);
  }
}

// Views
function showView(view) {
  const analyzeView = document.getElementById('analyzeView');
  const historyView = document.getElementById('historyView');
  
  if (view === 'history') {
    analyzeView.style.display = 'none';
    historyView.style.display = 'block';
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-item')[1].classList.add('active');
  } else {
    analyzeView.style.display = 'block';
    historyView.style.display = 'none';
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-item')[0].classList.add('active');
  }
}

// History
async function showHistory() {
  showView('history');
  const grid = document.getElementById('historyGrid');
  grid.innerHTML = '<p>Yuklanmoqda...</p>';
  
  try {
    const res = await fetch('/history');
    if (res.status === 401) {
      location.href = '/login';
      return;
    }
    const data = await res.json();
    grid.innerHTML = '';
    if (data.length === 0) {
      grid.innerHTML = "<p>Tarix bo'sh.</p>";
      return;
    }
    data.forEach(item => {
      const card = document.createElement('div');
      card.className = 'history-card glass-card';
      card.onclick = () => loadHistoryItem(item);
      card.innerHTML = `
        <img src="${item.image_path}" class="history-img">
        <div class="history-body">
          <div class="history-title">${item.result.disease} (${item.result.confidence}%)</div>
          <div class="history-date">${new Date(item.timestamp).toLocaleString()}</div>
          <p style="font-size:0.85rem; color:var(--text2); margin-top:0.5rem;">${item.result.description.substring(0, 100)}...</p>
        </div>
      `;
      grid.appendChild(card);
    });
  } catch (err) {
    grid.innerHTML = '<p>Xatolik yuz berdi.</p>';
  }
}

function loadHistoryItem(item) {
  showView('analyze');
  document.getElementById('uploadZone').style.display = 'none';
  document.getElementById('previewWrap').classList.add('show');
  document.getElementById('patientInfoWrap').classList.remove('show');
  document.getElementById('previewImg').src = item.image_path;
  document.getElementById('previewFname').textContent = "Tarixdan yuklandi";
  document.getElementById('analyzeBtn').disabled = true;
  document.querySelector('.analyze-cta-wrap').style.display = 'none';
  
  showResults(item.result);
}

// Analysis
function startAnalysis() {
  const file = window._selectedFile;
  const age = document.getElementById('patientAge').value;
  const gender = document.getElementById('patientGender').value;

  if (!file) {
    alert('Iltimos, avval rasm yuklang.');
    return;
  }
  if (!age) {
    alert('Iltimos, bemor yoshini kiriting.');
    return;
  }

  document.getElementById('analyzeBtn').disabled = true;
  document.getElementById('progCard').classList.add('show');
  ['resultsCard','recCard'].forEach(id => document.getElementById(id).classList.remove('show'));

  const predictPromise = (async () => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('age', String(age));
      formData.append('gender', String(gender));

      console.log('Sending request to /predict...', { age, gender });

      const res = await fetch('/predict', {
        method: 'POST',
        body: formData
      });
      if (res.status === 401) {
        location.href = '/login';
        return;
      }
      if (!res.ok) throw new Error('Server xatosi: ' + res.status);
      return await res.json();
    } catch (err) {
      console.error(err);
      return { error: err.message || 'Tarmoq xatosi' };
    }
  })();

  const steps = [{id:'s1',pct:20},{id:'s2',pct:40},{id:'s3',pct:62},{id:'s4',pct:84},{id:'s5',pct:100}];
  let i = 0;
  function tick() {
    if (i > 0) document.getElementById(steps[i-1].id).className = 'step done';
    if (i >= steps.length) {
      predictPromise.then(data => {
        if (data && !data.error) {
          showResults(data);
          updateSidebarHistory();
        } else {
          alert(data.error || 'Natija olinmadi');
          document.getElementById('analyzeBtn').disabled = false;
        }
      });
      return;
    }
    document.getElementById(steps[i].id).className = 'step active';
    document.getElementById('progFill').style.width = steps[i].pct + '%';
    document.getElementById('progPct').textContent = steps[i].pct + '%';
    i++;
    setTimeout(tick, 750);
  }
  tick();
}

function showResults(data) {
  document.getElementById('analyzeBtn').disabled = false;
  document.getElementById('progCard').classList.remove('show');
  document.getElementById('resultsCard').classList.add('show');
  document.getElementById('recCard').classList.add('show');
  document.querySelector('.analyze-cta-wrap').style.display = 'none';

  document.getElementById('resDisease').textContent = data.disease;
  document.getElementById('resConf').textContent = data.confidence + '%';
  document.getElementById('resDesc').textContent = data.description;

  const recList = document.getElementById('resRecs');
  recList.innerHTML = '';
  if (data.recommendation && Array.isArray(data.recommendation)) {
    data.recommendation.forEach(r => {
      const li = document.createElement('li');
      li.style.padding = '8px 0';
      li.style.borderBottom = '1px solid var(--border)';
      li.style.color = 'var(--text2)';
      li.innerHTML = `• ${r}`;
      recList.appendChild(li);
    });
  }
}

function resetAll() {
  window._selectedFile = null;
  document.getElementById('patientAge').value = '';
  document.getElementById('uploadZone').style.display = 'block';
  document.getElementById('previewWrap').classList.remove('show');
  document.getElementById('patientInfoWrap').classList.remove('show');
  document.getElementById('analyzeBtn').disabled = true;
  document.querySelector('.analyze-cta-wrap').style.display = 'block';
  ['progCard','resultsCard','recCard'].forEach(id => document.getElementById(id).classList.remove('show'));
  showView('analyze');
}

