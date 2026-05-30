// group-password.js
// 더미 데이터 제거 — 모든 검증은 서버에서 처리

// 초대 코드 검증 후 다음 단계로 넘길 그룹 정보 임시 저장
// { groupId, name, hasPassword, code } 형태
let pendingGroup = null;

// 버튼 로딩 상태 헬퍼
function setLoading(btnId, loading, label) {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    btn.disabled = loading;
    btn.textContent = loading ? '확인 중...' : label;
}

function showModalErr(id, msg) {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerText  = msg;
    el.style.display = msg ? 'block' : 'none';
}

// =================================================================
// STEP 1 : 초대 코드 모달 열기
// =================================================================
function openPasswordModal() {
    pendingGroup = null;

    const modal = document.getElementById('inviteModal');
    modal.classList.remove('hidden');
    modal.style.display = 'flex';

    document.getElementById('inviteCode').value = '';
    showModalErr('inviteError', '');
    document.getElementById('inviteCode').focus();
}

function closeModal() {
    ['inviteModal', 'passwordModal'].forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        el.classList.add('hidden');
        el.style.display = 'none';
    });
    pendingGroup = null;
}

// =================================================================
// STEP 2 : 초대 코드 검증 → 서버 POST /api/groups/verify-invite
// =================================================================
async function submitInviteCode() {
    const code = document.getElementById('inviteCode').value.trim().toUpperCase();

    if (!code) {
        showModalErr('inviteError', '초대 코드를 입력해 주세요.');
        return;
    }

    setLoading('inviteSubmitBtn', true, '확인');

    try {
        const res  = await fetch('/api/groups/verify-invite', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ code })
        });
        const data = await res.json();

        if (!data.ok) {
            showModalErr('inviteError', data.message || '유효하지 않은 초대 코드입니다.');
            return;
        }

        // 서버 응답에서 그룹 정보 저장 (비밀번호는 포함되지 않음)
        pendingGroup = {
            code,
            groupId:     data.groupId,
            name:        data.name,
            hasPassword: data.hasPassword
        };

        // 초대 코드 모달 닫기
        document.getElementById('inviteModal').classList.add('hidden');
        document.getElementById('inviteModal').style.display = 'none';

        if (data.hasPassword) {
            openGroupPasswordModal();   // 비밀번호 모달로
        } else {
            await enterGroup();         // 바로 입장
        }

    } catch (e) {
        showModalErr('inviteError', '서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.');
    } finally {
        setLoading('inviteSubmitBtn', false, '확인');
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
    showModalErr('passwordError', '');

    const nameEl = document.getElementById('pwModalGroupName');
    if (nameEl && pendingGroup) nameEl.textContent = `'${pendingGroup.name}'`;

    document.getElementById('groupPassword').focus();
}

// =================================================================
// STEP 4 : 비밀번호 제출 → 서버 POST /api/groups/join
// =================================================================
async function submitPassword() {
    const password = document.getElementById('groupPassword').value;

    if (!password) {
        showModalErr('passwordError', '비밀번호를 입력해 주세요.');
        return;
    }

    setLoading('passwordSubmitBtn', true, '입장');
    await enterGroup(password);
    setLoading('passwordSubmitBtn', false, '입장');
}

// =================================================================
// STEP 5 : 실제 입장 처리 → 서버 POST /api/groups/join
// =================================================================
async function enterGroup(password = '') {
    if (!pendingGroup) return;

    try {
        const res  = await fetch('/api/groups/join', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({
                code:     pendingGroup.code,
                password: password
            })
        });
        const data = await res.json();

        if (!data.ok) {
            // 비밀번호 오류는 비밀번호 모달에 표시
            if (pendingGroup.hasPassword) {
                showModalErr('passwordError', data.message || '비밀번호가 올바르지 않습니다.');
                document.getElementById('groupPassword').value = '';
                document.getElementById('groupPassword').focus();
            } else {
                showModalErr('inviteError', data.message || '그룹 입장에 실패했습니다.');
            }
            return;
        }

        // 성공 — 세션에 그룹 정보 저장 후 페이지 이동
        sessionStorage.setItem('groupId',   data.groupId);
        sessionStorage.setItem('groupName', data.name);

        closeModal();
        alert(`'${data.name}' 그룹에 입장했습니다!`);

        // 랭킹 페이지로 이동 (그룹 정보 반영)
        location.href = `rank.html`;

    } catch (e) {
        const errId = pendingGroup?.hasPassword ? 'passwordError' : 'inviteError';
        showModalErr(errId, '서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.');
    }
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
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') closeModal();
    });

    // Enter 키 지원
    document.getElementById('inviteCode')?.addEventListener('keydown', e => {
        if (e.key === 'Enter') submitInviteCode();
    });
    document.getElementById('groupPassword')?.addEventListener('keydown', e => {
        if (e.key === 'Enter') submitPassword();
    });
});