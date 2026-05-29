// group-password.js

// =================================================================
// 더미 그룹 데이터 (실제 서비스에서는 서버 API로 대체)
// =================================================================
const DUMMY_GROUPS = {
    "FOCUS-001": { name: "캡스톤 디자인 A팀", hasPassword: true,  password: "1234" },
    "FOCUS-002": { name: "토익 스터디 모임",  hasPassword: false, password: null   },
    "FOCUS-003": { name: "공무원 시험 준비반", hasPassword: true,  password: "9999" },
    "FOCUS-004": { name: "알고리즘 스터디",   hasPassword: false, password: null   },
};

// 초대 코드 검증 후 다음 단계로 넘길 그룹 정보 임시 저장
let pendingGroup = null;

// =================================================================
// STEP 1 : 초대 코드 모달
// =================================================================
function openPasswordModal() {
    pendingGroup = null;

    const modal = document.getElementById('inviteModal');
    modal.classList.remove('hidden');
    modal.style.display = 'flex';

    document.getElementById('inviteCode').value = '';
    const err = document.getElementById('inviteError');
    if (err) err.style.display = 'none';

    document.getElementById('inviteCode').focus();
}

function closeModal() {
    ['inviteModal', 'passwordModal'].forEach(id => {
        const modal = document.getElementById(id);
        if (!modal) return;
        modal.classList.add('hidden');
        modal.style.display = 'none';
    });
    pendingGroup = null;
}

// =================================================================
// STEP 2 : 초대 코드 검증 → 비밀번호 유무 분기
// =================================================================
function submitInviteCode() {
    const code = document.getElementById('inviteCode').value.trim().toUpperCase();
    const err  = document.getElementById('inviteError');

    if (!code) {
        if (err) { err.innerText = '초대 코드를 입력해 주세요.'; err.style.display = 'block'; }
        return;
    }

    const group = DUMMY_GROUPS[code];

    if (!group) {
        if (err) { err.innerText = '유효하지 않은 초대 코드입니다. 다시 확인해 주세요.'; err.style.display = 'block'; }
        return;
    }

    // 유효한 코드 저장
    pendingGroup = { code, ...group };

    // 초대 코드 모달 닫기
    const inviteModal = document.getElementById('inviteModal');
    inviteModal.classList.add('hidden');
    inviteModal.style.display = 'none';

    if (group.hasPassword) {
        // 비밀번호가 있는 그룹 → 비밀번호 모달로
        openGroupPasswordModal();
    } else {
        // 비밀번호 없는 그룹 → 바로 입장
        enterGroup();
    }
}

// =================================================================
// STEP 3 : 비밀번호 모달 (비밀번호 있는 그룹만)
// =================================================================
function openGroupPasswordModal() {
    const modal = document.getElementById('passwordModal');
    modal.classList.remove('hidden');
    modal.style.display = 'flex';

    document.getElementById('groupPassword').value = '';
    const err = document.getElementById('modalError');
    if (err) err.style.display = 'none';

    // 모달 안 그룹명 표시
    const nameEl = document.getElementById('pwModalGroupName');
    if (nameEl && pendingGroup) nameEl.textContent = `'${pendingGroup.name}'`;

    document.getElementById('groupPassword').focus();
}

function submitPassword() {
    const val = document.getElementById('groupPassword').value;
    const err = document.getElementById('modalError');

    if (!val) {
        if (err) { err.innerText = '비밀번호를 입력해 주세요.'; err.style.display = 'block'; }
        return;
    }

    if (!pendingGroup || val !== pendingGroup.password) {
        if (err) { err.innerText = '비밀번호가 올바르지 않습니다.'; err.style.display = 'block'; }
        document.getElementById('groupPassword').value = '';
        document.getElementById('groupPassword').focus();
        return;
    }

    closeModal();
    enterGroup();
}

// =================================================================
// STEP 4 : 그룹 입장
// =================================================================
function enterGroup() {
    if (!pendingGroup) return;
    // TODO: 실제 서비스에서는 서버 API로 입장 처리 후 페이지 이동
    alert(`'${pendingGroup.name}' 그룹에 입장했습니다!`);
    pendingGroup = null;
}

// =================================================================
// 이벤트 리스너
// =================================================================
document.addEventListener('DOMContentLoaded', () => {
    // 모달 바깥 클릭 시 닫기
    ['inviteModal', 'passwordModal'].forEach(id => {
        const modal = document.getElementById(id);
        if (!modal) return;
        modal.addEventListener('click', function(e) {
            if (e.target === this) closeModal();
        });
    });

    // ESC 키로 닫기
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });

    // Enter 키 지원
    document.getElementById('inviteCode')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') submitInviteCode();
    });
    document.getElementById('groupPassword')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') submitPassword();
    });
});
