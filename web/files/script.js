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

    // 리포트 대시보드 차트의 색상 변환 갱신을 위한 안전 장치
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

        // 1. 선형 차트
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

        // 2. 막대 차트
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

        // 3. 레이더 차트
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

        // 4. 도넛 차트
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

/* ... 기존 조원들의 script.js 내용 유지 ... */

// =================================================================
// 💡 추가: 유저 정보 드롭다운 및 탈퇴 인터랙션 제어
// =================================================================

// 드롭다운 온/오프 토글
function toggleUserDropdown(e) {
    e.preventDefault();
    e.stopPropagation();
    const dropdown = document.getElementById('userDropdown');
    if (dropdown) {
        dropdown.classList.toggle('show');
    }
}

// 스터디 그룹 탈퇴 처리
function handleLeaveGroup(e) {
    e.preventDefault();
    if (confirm("정말로 현재 소속된 스터디 그룹에서 탈퇴하시겠습니까?")) {
        alert("그룹 탈퇴가 완료되었습니다.");
        const dropdown = document.getElementById('userDropdown');
        if (dropdown) dropdown.classList.remove('show');
        // 추후 이곳에 백엔드 API 연동 구현 예정
    }
}

// 서비스 회원 탈퇴 처리
function handleDeleteAccount(e) {
    e.preventDefault();
    if (confirm("⚠️ 정말로 FocusMate 서비스를 탈퇴하시겠습니까?\n탈퇴 시 모든 몰입 데이터와 랭킹 기록이 영구 삭제됩니다.")) {
        alert("회원 탈퇴가 정상 처리되었습니다. 이용해 주셔서 감사합니다.");
        sessionStorage.removeItem('nickname');
        location.href = 'index.html';
    }
}

// 빈 공간 이중 클릭 또는 외부 영역 터치 시 드롭다운 자동 폐쇄
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
// 💡 추가: sessionStorage 닉네임 → 드롭다운 실시간 반영
//    (main-home, control, rank, report 공통 적용)
// =================================================================
document.addEventListener('DOMContentLoaded', () => {
    const nickname = sessionStorage.getItem('nickname');
    if (!nickname) return;

    // 트리거 버튼 텍스트 교체
    const trigger = document.getElementById('userTrigger');
    if (trigger) {
        trigger.textContent = `👤 ${nickname}님 ▾`;
    }

    // 드롭다운 내 이름/이메일 영역 교체
    const nameEl = document.querySelector('.user-info-name');
    if (nameEl) nameEl.textContent = nickname;

    const emailEl = document.querySelector('.user-info-email');
    if (emailEl) emailEl.textContent = `${nickname}@focusmate`;
});