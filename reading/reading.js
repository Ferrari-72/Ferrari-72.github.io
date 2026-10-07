(() => {
  const search = document.querySelector('#paper-search');
  const filters = [...document.querySelectorAll('[data-paper-filter]')];
  const papers = [...document.querySelectorAll('.paper-item')];
  const count = document.querySelector('#paper-count');
  const empty = document.querySelector('#paper-empty');

  if (!search || !filters.length || !papers.length || !count || !empty) return;

  let activeCategory = 'all';

  const updatePapers = () => {
    const query = search.value.trim().toLocaleLowerCase();
    let visible = 0;

    papers.forEach((paper) => {
      const categoryMatches = activeCategory === 'all' || paper.dataset.paperCategory === activeCategory;
      const searchMatches = !query || paper.textContent.toLocaleLowerCase().includes(query);
      const show = categoryMatches && searchMatches;
      paper.hidden = !show;
      if (show) visible += 1;
    });

    count.textContent = `Showing ${visible} ${visible === 1 ? 'paper' : 'papers'}`;
    empty.hidden = visible !== 0;
  };

  filters.forEach((button) => {
    button.addEventListener('click', () => {
      activeCategory = button.dataset.paperFilter;
      filters.forEach((item) => item.setAttribute('aria-pressed', String(item === button)));
      updatePapers();
    });
  });

  search.addEventListener('input', updatePapers);
})();
