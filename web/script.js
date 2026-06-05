// script.js

// =================================================================
// 1. 전역 라이트/다크모드 상태 관리 시스템 (이모지 아이콘 통합 버전)
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

    if (document.getElementById('lineChart')) {
        location.reload(); 
    }
}

function updateToggleBtnIcon(theme) {
    const btn = document.getElementById("themeToggleBtn");
    if (btn) {
        btn.innerText = theme === "dark" ? "☀️" : "🌙";
    }
}

// =================================================================
// 2. 요소 제어 및 스크롤 감지 애니메이션
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

function startAI() {
    const feed = document.getElementById('camFeed');
    const msg = document.getElementById('msg-text');
    if (feed && msg) {
        feed.style.background = "#000";
        feed.innerHTML = "<div style='color:var(--primary); font-weight:800; animation: blink 1.5s infinite;'>● LIVE ANALYSIS</div>";
        msg.innerText = "분석 엔진이 활성화되었습니다. 실시간으로 집중도를 체크합니다.";
    }
}

function stopAI() {
    alert("세션을 종료하고 데이터를 원격 서버에 동기화합니다.");
}

// =================================================================
// 3. 고도화 멀티 시각화 차트 연동 로직 (Chart.js 패치 탑재)
// =================================================================
document.addEventListener("DOMContentLoaded", () => {
    const lineCanvas = document.getElementById('lineChart');
    const barCanvas = document.getElementById('barChart');
    const radarCanvas = document.getElementById('radarChart');
    const doughnutCanvas = document.getElementById('doughnutChart');

    if (lineCanvas && barCanvas && radarCanvas && doughnutCanvas) {
        const isDark = document.documentElement.getAttribute("data-theme") === "dark";
        const textColor = isDark ? "#94a3b8" : "#64748b";
        const gridColor = isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.05)";

        const commonOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { color: gridColor }, ticks: { color: textColor, font: { family: 'Pretendard' } } },
                y: { grid: { color: gridColor }, ticks: { color: textColor, font: { family: 'Pretendard' } }, min: 0, max: 100 }
            }
        };

        window.chartLine = new Chart(lineCanvas, {
            type: 'line',
            data: {
                labels: ['14:00', '14:15', '14:30', '14:45', '15:00'],
                datasets: [{
                    data: [65, 78, 92, 40, 88],
                    borderColor: '#009460',
                    backgroundColor: 'rgba(0, 148, 96, 0.08)',
                    fill: true,
                    tension: 0.35,
                    borderWidth: 3
                }]
            },
            options: commonOptions
        });

        window.chartBar = new Chart(barCanvas, {
            type: 'bar',
            data: {
                labels: ['월', '화', '수', '목', '금'],
                datasets: [{
                    data: [180, 240, 120, 310, 210],
                    backgroundColor: isDark ? '#334155' : '#e2e8f0',
                    hoverBackgroundColor: '#009460',
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { display: false }, ticks: { color: textColor } },
                    y: { grid: { color: gridColor }, ticks: { color: textColor } }
                }
            }
        });

        window.chartRadar = new Chart(radarCanvas, {
            type: 'radar',
            data: {
                labels: ['시선 고정', '자세 바름', '눈 깜빡임', '집중 유지', '흐트러짐 방지'],
                datasets: [{
                    data: [90, 75, 85, 95, 60],
                    backgroundColor: 'rgba(0, 148, 96, 0.15)',
                    borderColor: '#009460',
                    pointBackgroundColor: '#009460',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    r: {
                        grid: { color: gridColor },
                        angleLines: { color: gridColor },
                        pointLabels: { color: textColor, font: { size: 11, family: 'Pretendard', weight: '600' } },
                        ticks: { display: false },
                        suggestedMin: 0,
                        suggestedMax: 100
                    }
                }
            }
        });

        window.chartDoughnut = new Chart(doughnutCanvas, {
            type: 'doughnut',
            data: {
                labels: ['순수집중', '졸음 대기', '시선 이탈'],
                datasets: [{
                    data: [80, 12, 8],
                    backgroundColor: ['#009460', '#f59e0b', '#ef4444'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'bottom', labels: { color: textColor, font: { family: 'Pretendard' } } } },
                cutout: '70%'
            }
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
        window.chartDoughnut.data.datasets[0].data[0] = value;
        window.chartDoughnut.data.datasets[0].data[1] = Math.floor(rest * 0.6);
        window.chartDoughnut.data.datasets[0].data[2] = Math.floor(rest * 0.4);
        window.chartDoughnut.update();
    } else if (type === 'progress') {
        const bar = document.getElementById('progress-bar');
        const txt = document.getElementById('progress-percent');
        if(bar && txt) {
            bar.style.width = value + '%';
            txt.innerText = value + '%';
        }
    }
}

// =================================================================
// 4. 유저 정보 드롭다운 및 탈퇴 인터랙션 제어
// =================================================================
function toggleUserDropdown(e) {
    e.preventDefault();
    e.stopPropagation();
    const dropdown = document.getElementById('userDropdown');
    if (dropdown) {
        dropdown.classList.toggle('show');
    }
}

function handleLeaveGroup(e) {
    e.preventDefault();
    if (confirm("정말로 현재 소속된 스터디 그룹에서 탈퇴하시겠습니까?")) {
        fetch('/api/groups/leave', { method: 'POST', credentials: 'include' })
            .then(res => res.json())
            .then(data => {
                if (data.ok) {
                    sessionStorage.removeItem('groupId');
                    sessionStorage.removeItem('groupName');
                    alert("그룹 탈퇴가 완료되었습니다.");
                    updateGroupNavLink(null); // 탈퇴 후 링크 → create-group
                    location.reload();
                } else {
                    alert(data.message || "탈퇴 처리 중 오류가 발생했습니다.");
                }
            })
            .catch(() => alert("서버에 연결할 수 없습니다."));
        const dropdown = document.getElementById('userDropdown');
        if (dropdown) dropdown.classList.remove('show');
    }
}

function handleDeleteAccount(e) {
    e.preventDefault();
    if (confirm("⚠️ 정말로 FocusMate 서비스를 탈퇴하시겠습니까?\n탈퇴 시 모든 몰입 데이터와 랭킹 기록이 영구 삭제됩니다.")) {
        alert("회원 탈퇴가 정상 처리되었습니다. 이용해 주셔서 감사합니다.");
        sessionStorage.clear();
        location.href = 'index.html';
    }
}

function handleLogout(e) {
    e.preventDefault();
    fetch('/logout', { method: 'POST', credentials: 'include' })
        .then(() => {
            sessionStorage.clear();
            location.href = 'index.html';
        })
        .catch(() => {
            sessionStorage.clear();
            location.href = 'index.html';
        });
}

document.addEventListener('click', function(e) {
    const dropdown = document.getElementById('userDropdown');
    const trigger = document.getElementById('userTrigger');
    if (dropdown && dropdown.classList.contains('show')) {
        if (!dropdown.contains(e.target) && e.target !== trigger) {
            dropdown.classList.remove('show');
        }
    }
});

// =================================================================
// 5. 그룹 네비게이션 링크 동적 변경
//    - 그룹 있음 → group-dashboard.html
//    - 그룹 없음 → create-group.html
// =================================================================
function updateGroupNavLink(groupId) {
    // 헤더 nav 안의 그룹 링크 찾기 (href에 group 포함된 a 태그)
    const groupLinks = document.querySelectorAll('nav a[href*="group"]');
    groupLinks.forEach(link => {
        if (groupId) {
            link.href = 'group-dashboard.html';
            link.title = '내 그룹 대시보드';
        } else {
            link.href = 'create-group.html';
            link.title = '그룹 만들기 / 입장';
        }
    });
}

// =================================================================
// 6. 닉네임 → 드롭다운 실시간 반영 + 그룹 링크 동적 적용
// =================================================================
function applyNickname(nickname) {
    const trigger = document.getElementById('userTrigger');
    if (trigger) trigger.textContent = nickname ? `👤 ${nickname}님 ▾` : '👤 로그인';

    const nameEl = document.querySelector('.user-info-name');
    if (nameEl) nameEl.textContent = nickname || '';

    const emailEl = document.querySelector('.user-info-email');
    if (emailEl) emailEl.textContent = nickname || '';
}

document.addEventListener('DOMContentLoaded', async () => {
    if (!document.getElementById('userTrigger')) return;

    applyNickname('');

    try {
        const res = await fetch('/me', { credentials: 'include' });
        if (res.ok) {
            const data = await res.json();
            if (data.ok && data.nickname) {
                sessionStorage.setItem('nickname', data.nickname);
                sessionStorage.setItem('user_id',  data.user_id);
                if (data.group_id) {
                    sessionStorage.setItem('groupId', data.group_id);
                } else {
                    sessionStorage.removeItem('groupId');
                }
                applyNickname(data.nickname);
                updateGroupNavLink(data.group_id); // ★ 그룹 링크 적용
                return;
            }
        }
    } catch (_) { /* 서버 없을 때 fallback */ }

    // fallback: sessionStorage
    const saved = sessionStorage.getItem('nickname');
    const savedGroupId = sessionStorage.getItem('groupId');
    if (saved) {
        applyNickname(saved);
        updateGroupNavLink(savedGroupId); // ★ 그룹 링크 적용
    } else {
        applyNickname('');
        updateGroupNavLink(null);
    }
});