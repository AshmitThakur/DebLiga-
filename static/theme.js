(function () {
    const storageKey = 'theme';
    const root = document.documentElement;
    const toggle = document.querySelector('.theme-toggle');
    const icon = document.querySelector('.theme-toggle-icon');
    const label = document.querySelector('.theme-toggle-label');
    const sunIcon = `<svg viewBox='0 0 24 24' aria-hidden='true'><circle cx='12' cy='12' r='4'></circle><path d='M12 2v2m0 16v2M2 12h2m16 0h2M5 5l2 2m10 10 2 2M5 19l2-2M17 7l2-2'></path></svg>`;
    const moonIcon = `<svg viewBox='0 0 24 24' aria-hidden='true'><path d='M20 15A8 8 0 0 1 9 4a8 8 0 1 0 11 11Z'></path></svg>`;

    const applyTheme = function (theme) {
        root.setAttribute('data-theme', theme);
        if (toggle) {
            const dark = theme === 'dark';
            toggle.innerHTML = dark ? sunIcon : moonIcon;
            toggle.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
            toggle.title = toggle.getAttribute('aria-label');
            return;
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
    const nav = document.querySelector('.top-navigation, body > nav');
    if (nav) {
        const menuIcon = `<svg viewBox='0 0 24 24' aria-hidden='true'><path d='M4 7h16M4 12h16M4 17h16'></path></svg>`;
        const closeIcon = `<svg viewBox='0 0 24 24' aria-hidden='true'><path d='m6 6 12 12M18 6 6 18'></path></svg>`;
        nav.id = nav.id || 'site-navigation';
        const button = document.createElement('button'), overlay = document.createElement('button');
        button.className = 'menu-toggle'; button.type = 'button'; button.innerHTML = menuIcon;
        button.setAttribute('aria-controls', nav.id); overlay.className = 'nav-overlay'; overlay.type = 'button';
        overlay.setAttribute('aria-label', 'Close navigation menu'); nav.before(button); document.body.appendChild(overlay);
        function openMenu(open) {
            document.body.classList.toggle('nav-open', open); button.innerHTML = open ? closeIcon : menuIcon;
            button.setAttribute('aria-expanded', String(open));
            button.setAttribute('aria-label', open ? 'Close navigation menu' : 'Open navigation menu');
        }
        openMenu(false);
        button.onclick = function () { openMenu(!document.body.classList.contains('nav-open')); };
        overlay.onclick = function () { openMenu(false); };
        nav.onclick = function (event) { if (event.target.closest('a')) openMenu(false); };
        document.addEventListener('keydown', function (event) { if (event.key === 'Escape') openMenu(false); });
        window.matchMedia('(min-width: 721px)').addEventListener('change', function (event) { if (event.matches) openMenu(false); });
    }
    const teamEmojis = {
        'Panel Pls Understand': '\u{1F3A4}', 'Tappu Sena': '\u2694\uFE0F',
        'The Nexus': '\u{1F53A}', 'Court of Reason': '\u2696\uFE0F',
        'The Orators of Olympus': '\u26A1', 'Meow Meow': '\u{1F431}',
        'Icarus': '\u{1FABD}', 'Phuss Phuss Gang': '\u{1F4A8}'
    };
    document.querySelectorAll('.standings-pool tbody td:nth-child(2) a').forEach(function (team) {
        const name = team.textContent.trim();
        if (teamEmojis[name]) team.textContent = teamEmojis[name] + ' ' + name;
    });
    document.querySelectorAll('.hall-of-fame-item').forEach(function (item) {
        const year = item.querySelector('.hall-of-fame-year');
        const team = item.querySelector('.hall-of-fame-team');
        if (year && team && year.textContent.trim() === '2025' && team.textContent.trim() === 'Panel Pls Understand') {
            item.classList.add('hall-of-fame-champion');
            team.textContent = '\u{1F3C6} Panel Pls Understand';
        }
    });
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    function animatePage() {
        if (reduceMotion.matches) return;
        window.gsap.registerPlugin(window.ScrollTrigger);
        const selector = document.querySelector('.history-page')
            ? '.history-page > section, .flow-card, .value-card, .hall-of-fame-item, .auction-team-card, .top-purchase-card, .history-page img'
            : '.dashboard-section, .dashboard-card, .about-section, .auction-promo, .hall-of-fame-item, .hero-visual';
        window.gsap.utils.toArray(selector).forEach(function (element) {
            window.gsap.from(element, {autoAlpha: 0, y: 18, duration: 0.65, ease: 'power2.out', scrollTrigger: {trigger: element, start: 'top 88%', once: true}});
        });
    }
    if (document.querySelector('.hero-section, .history-page') && !reduceMotion.matches) {
        const gsap = document.createElement('script');
        gsap.src = 'https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js';
        gsap.onload = function () {
            const trigger = document.createElement('script');
            trigger.src = 'https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/ScrollTrigger.min.js';
            trigger.onload = animatePage;
            document.head.appendChild(trigger);
        };
        document.head.appendChild(gsap);
    }
})();
