(() => {
  const root = document.documentElement;
  const themeButton = document.querySelector('.theme-toggle');
  const themeLabel = document.querySelector('.theme-label');
  const themeColor = document.querySelector('meta[name="theme-color"]');
  const storedTheme = localStorage.getItem('theme');
  const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

  function applyTheme(theme) {
    const dark = theme === 'dark';
    root.dataset.theme = theme;
    themeButton.setAttribute('aria-pressed', String(dark));
    themeButton.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
    themeLabel.textContent = dark ? 'Light' : 'Dark';
    themeColor.setAttribute('content', dark ? '#181817' : '#f7f7f5');
  }

  applyTheme(storedTheme || (systemPrefersDark ? 'dark' : 'light'));

  themeButton.addEventListener('click', () => {
    const nextTheme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    applyTheme(nextTheme);
    localStorage.setItem('theme', nextTheme);
  });

  const filterButtons = [...document.querySelectorAll('[data-filter]')];
  const researchEntries = [...document.querySelectorAll('#research-list .entry')];
  const researchList = document.querySelector('#research-list');
  const sortButtons = [...document.querySelectorAll('[data-research-sort]')];

  function sortResearch(direction) {
    const multiplier = direction === 'desc' ? -1 : 1;
    researchEntries
      .slice()
      .sort((a, b) => (Number(a.dataset.sequence) - Number(b.dataset.sequence)) * multiplier)
      .forEach((entry) => researchList.append(entry));
  }

  if (researchList && researchEntries.length) sortResearch('asc');

  filterButtons.forEach((button) => {
    button.addEventListener('click', () => {
      const filter = button.dataset.filter;

      filterButtons.forEach((item) => {
        item.setAttribute('aria-pressed', String(item === button));
      });

      researchEntries.forEach((entry) => {
        const topics = entry.dataset.topics.split(' ');
        entry.hidden = filter !== 'all' && !topics.includes(filter);
      });
    });
  });

  sortButtons.forEach((button) => {
    button.addEventListener('click', () => {
      sortButtons.forEach((item) => {
        item.setAttribute('aria-pressed', String(item === button));
      });
      sortResearch(button.dataset.researchSort);
    });
  });

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const revealItems = [...document.querySelectorAll(
    '.intro-copy, .details, .reading-intro, .section-label, .prose, .news-list li, .research-tools, .entry, .reading-controls, .paper-item, footer'
  )];

  if (!reduceMotion && 'IntersectionObserver' in window) {
    const revealObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        entry.target.classList.toggle('is-visible', entry.isIntersecting);
      });
    }, { rootMargin: '-5% 0px -10% 0px', threshold: 0.1 });

    revealItems.forEach((item) => {
      item.classList.add('reveal-on-scroll');
      if (item.getBoundingClientRect().top < window.innerHeight * 0.9) {
        item.classList.add('is-visible');
      }
      revealObserver.observe(item);
    });
  }

  const navLinks = [...document.querySelectorAll('nav a[href^="#"]')];
  const observedSections = navLinks
    .map((link) => document.querySelector(link.getAttribute('href')))
    .filter(Boolean);

  const sectionObserver = new IntersectionObserver((entries) => {
    const visible = entries
      .filter((entry) => entry.isIntersecting)
      .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];

    if (!visible) return;

    navLinks.forEach((link) => {
      const active = link.getAttribute('href') === `#${visible.target.id}`;
      link.classList.toggle('active', active);
      if (active) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
  }, { rootMargin: '-20% 0px -65% 0px', threshold: [0, 0.2, 0.5] });

  observedSections.forEach((section) => sectionObserver.observe(section));

  const backToTop = document.querySelector('.back-to-top');

  function updateBackToTop() {
    backToTop.classList.toggle('visible', window.scrollY > 700);
  }

  window.addEventListener('scroll', updateBackToTop, { passive: true });
  updateBackToTop();

  backToTop.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
})();
