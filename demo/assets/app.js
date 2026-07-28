(() => {
  const table = document.querySelector("#change-table");
  if (!table) return;
  const rows = [...table.querySelectorAll("tbody tr")];
  const search = document.querySelector("#search");
  const category = document.querySelector("#category");
  const materiality = document.querySelector("#materiality");
  const novelty = document.querySelector("#novelty");
  const count = document.querySelector("#result-count");
  const empty = document.querySelector("#empty");
  const apply = () => {
    const query = search.value.trim().toLowerCase();
    let visible = 0;
    rows.forEach((row) => {
      const matches = (!query || row.textContent.toLowerCase().includes(query))
        && (!category.value || row.dataset.category === category.value)
        && (!materiality.value || row.dataset.materiality === materiality.value)
        && (!novelty.value || row.dataset.novelty === novelty.value);
      row.hidden = !matches;
      if (matches) visible += 1;
    });
    count.textContent = `${visible} of ${rows.length} evidence-backed changes`;
    empty.style.display = visible ? "none" : "block";
  };
  [search, category, materiality, novelty].forEach((control) => {
    control.addEventListener(control.tagName === "INPUT" ? "input" : "change", apply);
  });
  apply();
})();
