(function () {
    const storageKey = 'theme';
    const root = document.documentElement;
    const toggle = document.querySelector('.theme-toggle');
    const icon = document.querySelector('.theme-toggle-icon');
    const label = document.querySelector('.theme-toggle-label');

    const applyTheme = function (theme) {
        root.setAttribute('data-theme', theme);
        if (toggle) {
            icon.textContent = theme === 'dark' ? '🌙' : '☀';
            label.textContent = theme === 'dark' ? 'Dark' : 'Light';
        }
    };

    const savedTheme = localStorage.getItem(storageKey);
    applyTheme(savedTheme === 'dark' ? 'dark' : 'light');

    if (toggle) {
        toggle.addEventListener('click', function () {
            const nextTheme = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
            applyTheme(nextTheme);
            localStorage.setItem(storageKey, nextTheme);
        });
    }
})();
