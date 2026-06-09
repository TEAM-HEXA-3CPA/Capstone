// script.js

// =================================================================
// JWT 토큰 관리 유틸리티
// =================================================================
const Auth = {
    setToken(token) {
        localStorage.setItem('fm_token', token);
        const exp = Date.now() + 30 * 60 * 1000;
        localStorage.setItem('fm_token_exp', exp);
    },
    getToken() {
        const token = localStorage.getItem('fm_token');
        const exp   = parseInt(localStorage.getItem('fm_token_exp') || '0');
        if (!token || Date.now() > exp) {
            this.clear();
            return null;
        }
        return token;
    },
    clear() {
        localStorage.removeItem('fm_token');
        localStorage.removeItem('fm_token_exp');
        sessionStorage.clear();
    },
    isLoggedIn() {
        return !!this.getToken();
    },
    // 남은 시간 (분:초 문자열)
    getRemainingTime() {
        const exp = parseInt(localStorage.getItem('fm_token_exp') || '0');
        const remaining = exp - Date.now();
        if (remaining <= 0) return null;
        const min = Math.floor(remaining / 60000);
        const sec = Math.floor((remaining % 60000) / 1000);
        return `${min}분 ${sec.toString().padStart(2, '0')}초`;
    },
    async fetch(url, options = {}) {
        const token = this.getToken();
        if (!options.headers) options.headers = {};
        if (token) options.headers['Authorization'] = `Bearer ${token}`;
        if (!(options.body instanceof FormData) && !options.headers['Content-Type']) {
            options.headers['Content-Type'] = 'application/json';
        }
        return fetch(url, options);
    }
};

// =================================================================
// 공개 페이지 여부
// =================================================================
function isPublicPage() {
    const page = location.pathname.split('/').pop() || 'index.html';
    return ['index.html', 'login.html', 'signup.html', ''].includes(page);
}

// =================================================================
// 30분 만료 자동 로그아웃 타이머
// =================================================================
function startAutoLogoutTimer() {
    const exp = parseInt(localStorage.getItem('fm_token_exp') || '0');
    const remaining = exp - Date.now();
    if (remaining <= 0) { doLogout(); return; }
    setTimeout(() => {
        alert('세션이 만료되었습니다. 다시 로그인해주세요.');
        doLogout();
    }, remaining);

    // 드롭다운 남은시간 1초마다 갱신
    if (document.getElementById('sessionTimerDisplay')) {
        setInterval(updateSessionTimer, 1000);
    }
}

function updateSessionTimer() {
    const el = document.getElementById('sessionTimerDisplay');
    if (!el) return;
    const t = Auth.getRemainingTime();
    if (!t) {
        el.textContent = '만료됨';
        el.style.color = '#ef4444';
    } else {
        el.textContent = t;
        const min = parseInt(t);
        el.style.color = min <= 5 ? '#ef4444' : 'var(--primary)';
    }
}

function doLogout() {
    Auth.clear();
    location.href = 'index.html';
}

// =================================================================
// 1. 라이트/다크모드
// =================================================================
document.addEventListener("DOMContentLoaded", () => {
    const savedTheme = localStorage.getItem("theme") || "light";
    document.documentElement.setAttribute("data-theme", savedTheme);
    updateToggleBtnIcon(savedTheme);
});

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
    const newTheme = currentTheme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", newTheme);
    localStorage.setItem("theme", newTheme);
    updateToggleBtnIcon(newTheme);
    if (document.getElementById('lineChart')) location.reload();
}

function updateToggleBtnIcon(theme) {
    const btn = document.getElementById("themeToggleBtn");
    if (btn) btn.innerText = theme === "dark" ? "☀️" : "🌙";
}

// =================================================================
// 2. 스크롤 애니메이션
// =================================================================
const items = document.querySelectorAll('.reveal');
if (items.length > 0) {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) entry.target.classList.add('active');
        });
    }, { threshold: 0.1 });
    items.forEach(el => observer.observe(el));
}

// =================================================================
// 3. 차트
// =================================================================
document.addEventListener("DOMContentLoaded", () => {
    const lineCanvas     = document.getElementById('lineChart');
    const barCanvas      = document.getElementById('barChart');
    const radarCanvas    = document.getElementById('radarChart');
    const doughnutCanvas = document.getElementById('doughnutChart');

    if (lineCanvas && barCanvas && radarCanvas && doughnutCanvas) {
        const isDark    = document.documentElement.getAttribute("data-theme") === "dark";
        const textColor = isDark ? "#94a3b8" : "#64748b";
        const gridColor = isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.05)";
        const commonOptions = {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { color: gridColor }, ticks: { color: textColor, font: { family: 'Pretendard' } } },
                y: { grid: { color: gridColor }, ticks: { color: textColor, font: { family: 'Pretendard' } }, min: 0, max: 100 }
            }
        };
        window.chartLine = new Chart(lineCanvas, {
            type: 'line',
            data: { labels: ['14:00','14:15','14:30','14:45','15:00'],
                    datasets: [{ data: [65,78,92,40,88], borderColor: '#009460',
                                 backgroundColor: 'rgba(0,148,96,0.08)', fill: true, tension: 0.35, borderWidth: 3 }] },
            options: commonOptions
        });
        window.chartBar = new Chart(barCanvas, {
            type: 'bar',
            data: { labels: ['월','화','수','목','금'],
                    datasets: [{ data: [180,240,120,310,210],
                                 backgroundColor: isDark ? '#334155' : '#e2e8f0',
                                 hoverBackgroundColor: '#009460', borderRadius: 6 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } },
                       scales: { x: { grid: { display: false }, ticks: { color: textColor } },
                                  y: { grid: { color: gridColor }, ticks: { color: textColor } } } }
        });
        window.chartRadar = new Chart(radarCanvas, {
            type: 'radar',
            data: { labels: ['시선 고정','자세 바름','눈 깜빡임','집중 유지','흐트러짐 방지'],
                    datasets: [{ data: [90,75,85,95,60], backgroundColor: 'rgba(0,148,96,0.15)',
                                 borderColor: '#009460', pointBackgroundColor: '#009460', borderWidth: 2 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } },
                       scales: { r: { grid: { color: gridColor }, angleLines: { color: gridColor },
                                       pointLabels: { color: textColor, font: { size: 11, family: 'Pretendard', weight: '600' } },
                                       ticks: { display: false }, suggestedMin: 0, suggestedMax: 100 } } }
        });
        window.chartDoughnut = new Chart(doughnutCanvas, {
            type: 'doughnut',
            data: { labels: ['순수집중','졸음 대기','시선 이탈'],
                    datasets: [{ data: [80,12,8], backgroundColor: ['#009460','#f59e0b','#ef4444'], borderWidth: 0 }] },
            options: { responsive: true, maintainAspectRatio: false, cutout: '70%',
                       plugins: { legend: { position: 'bottom', labels: { color: textColor, font: { family: 'Pretendard' } } } } }
        });
    }
});

function updateDemoData(type, val) {
    const value = parseInt(val);
    if (type === 'line' && window.chartLine) {
        window.chartLine.data.datasets[0].data[4] = value;
        window.chartLine.update();
    } else if (type === 'ratio' && window.chartDoughnut) {
        const rest = 100 - value;
        window.chartDoughnut.data.datasets[0].data = [value, Math.floor(rest*0.6), Math.floor(rest*0.4)];
        window.chartDoughnut.update();
    }
}

// =================================================================
// 4. 드롭다운 / 탈퇴 / 로그아웃
// =================================================================
function toggleUserDropdown(e) {
    e.preventDefault();
    e.stopPropagation();
    document.getElementById('userDropdown')?.classList.toggle('show');
}

function handleLeaveGroup(e) {
    e.preventDefault();
    if (!confirm("정말로 현재 소속된 스터디 그룹에서 탈퇴하시겠습니까?")) return;
    Auth.fetch('/api/groups/leave', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.ok) {
                sessionStorage.removeItem('groupId');
                sessionStorage.removeItem('groupName');
                alert("그룹 탈퇴가 완료되었습니다.");
                updateGroupNavLink(null);
                location.reload();
            } else {
                alert(data.message || "탈퇴 처리 중 오류가 발생했습니다.");
            }
        })
        .catch(() => alert("서버에 연결할 수 없습니다."));
    document.getElementById('userDropdown')?.classList.remove('show');
}

function handleDeleteAccount(e) {
    e.preventDefault();
    if (confirm("⚠️ 정말로 FocusMate 서비스를 탈퇴하시겠습니까?\n탈퇴 시 모든 데이터가 영구 삭제됩니다.")) {
        Auth.clear();
        alert("회원 탈퇴가 정상 처리되었습니다. 이용해 주셔서 감사합니다.");
        location.href = 'index.html';
    }
}

function handleLogout(e) {
    e.preventDefault();
    fetch('/logout', { method: 'POST' }).finally(() => {
        Auth.clear();
        location.href = 'index.html';
    });
}

document.addEventListener('click', function(e) {
    const dropdown = document.getElementById('userDropdown');
    const trigger  = document.getElementById('userTrigger');
    if (dropdown?.classList.contains('show')) {
        if (!dropdown.contains(e.target) && e.target !== trigger) {
            dropdown.classList.remove('show');
        }
    }
});

// =================================================================
// 5. 그룹 네비게이션 링크 동적 변경
// =================================================================
function updateGroupNavLink(groupId) {
    // href에 group이 포함된 nav 링크 전체 교체
    document.querySelectorAll('nav a').forEach(link => {
        const href = link.getAttribute('href') || '';
        if (href.includes('group') || href.includes('create-group') || href.includes('group-dashboard')) {
            link.href  = groupId ? 'group-dashboard.html' : 'create-group.html';
            link.title = groupId ? '내 그룹 대시보드' : '그룹 만들기 / 입장';
        }
    });
}

// =================================================================
// 6. 닉네임 반영 + 세션 타이머 삽입
// =================================================================
function applyNickname(nickname) {
    const trigger = document.getElementById('userTrigger');
    if (trigger) trigger.textContent = nickname ? `👤 ${nickname}님 ▾` : '👤 로그인';
    const nameEl  = document.querySelector('.user-info-name');
    if (nameEl)  nameEl.textContent  = nickname || '';
    const emailEl = document.querySelector('.user-info-email');
    if (emailEl) emailEl.textContent = nickname || '';
}

// 드롭다운 내부에 세션 타이머 행 삽입
function injectSessionTimer() {
    const summary = document.querySelector('.user-info-summary');
    if (!summary || document.getElementById('sessionTimerDisplay')) return;

    const timerRow = document.createElement('div');
    timerRow.style.cssText = 'font-size:0.75rem; color:var(--text-sub); margin-top:6px; display:flex; align-items:center; gap:6px;';
    timerRow.innerHTML = `
        <span>⏱ 세션 만료까지</span>
        <span id="sessionTimerDisplay" style="font-weight:700; color:var(--primary);">--:--</span>
    `;
    summary.appendChild(timerRow);

    // 즉시 1회 표시 후 1초마다 갱신
    updateSessionTimer();
    setInterval(updateSessionTimer, 1000);
}

// =================================================================
// 7. DOMContentLoaded — 인증 체크 + 닉네임 + 타이머
// =================================================================
document.addEventListener('DOMContentLoaded', async () => {
    if (!document.getElementById('userTrigger')) return;
    applyNickname('');
    if (isPublicPage()) return;

    if (!Auth.isLoggedIn()) {
        location.href = 'index.html';
        return;
    }

    startAutoLogoutTimer();
    injectSessionTimer();

    try {
        const res = await Auth.fetch('/me');
        if (res.ok) {
            const data = await res.json();
            if (data.ok && data.nickname) {
                sessionStorage.setItem('nickname', data.nickname);
                sessionStorage.setItem('user_id',  data.user_id);
                if (data.group_id) sessionStorage.setItem('groupId', data.group_id);
                else sessionStorage.removeItem('groupId');
                applyNickname(data.nickname);
                updateGroupNavLink(data.group_id);
                return;
            }
        }
        // 401(토큰 만료)일 때만 로그아웃, 네트워크 오류 등은 로컬 정보로 유지
        if (res.status === 401) {
            Auth.clear();
            location.href = 'index.html';
            return;
        }
        // 그 외 서버 오류 → localStorage 토큰 유지, sessionStorage로 fallback
        const saved = sessionStorage.getItem('nickname');
        if (saved) {
            applyNickname(saved);
            updateGroupNavLink(sessionStorage.getItem('groupId'));
        }
    } catch (_) {
        // 네트워크 오류 → 토큰 유지, sessionStorage로 fallback
        const saved = sessionStorage.getItem('nickname');
        if (saved) {
            applyNickname(saved);
            updateGroupNavLink(sessionStorage.getItem('groupId'));
        }
    }
});