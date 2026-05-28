// group-password.js

function openPasswordModal() {
    const modal = document.getElementById('passwordModal');
    modal.classList.remove('hidden');
    modal.style.display = 'flex';
    document.getElementById('groupPassword').value = '';
    const err = document.getElementById('modalError');
    if (err) err.style.display = 'none';
}

function closeModal() {
    const modal = document.getElementById('passwordModal');
    modal.classList.add('hidden');
    modal.style.display = 'none';
}
function submitPassword() {
    const val = document.getElementById('groupPassword').value;
    const err = document.getElementById('modalError');

    if (!val) {
        if (err) { err.innerText = '비밀번호를 입력해 주세요.'; err.style.display = 'block'; }
        return;
    }

    // TODO: 서버 API로 비밀번호 검증
    alert('그룹에 입장했습니다!');
    closeModal();
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('passwordModal').addEventListener('click', function(e) {
        if (e.target === this) closeModal();
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });

    document.getElementById('groupPassword').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') submitPassword();
    });
});