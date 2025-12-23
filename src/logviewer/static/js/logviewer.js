(() => {
  'use strict';

  const state = {
    offset: 0,
    limit: 100,
    loading: false,
    requestId: 0,
  };

  const getLimit = () => {
    const v = parseInt($('#q-limit').val() || '100', 10);
    return Number.isFinite(v) && v > 0 ? v : 100;
  };

  const getParams = (offset) => ({
    query: ($('#q-query').val() || '').trim(),
    level: $('#q-level').val() || '',
    source: $('#q-source').val() || 'django',
    limit: state.limit,
    offset,
  });

  const fetchLogs = async (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    const res = await fetch(`/api/logs/?${qs}`, { credentials: 'same-origin' });
    if (!res.ok) {
      const txt = await res.text().catch(() => '');
      alert(`Error: ${res.status} ${txt}`.trim());
      return null;
    }
    try {
      return await res.json();
    } catch {
      alert('Error: Invalid JSON response');
      return null;
    }
  };

  const renderRows = (items = []) => {
    const $tbody = $('#logs-table tbody');
    $tbody.empty();

    const rows = items.map((it, i) => {
      const number = state.offset + i + 1;
      const level = (it?.level || '').toUpperCase();
      const badgeClass =
        level === 'CRITICAL' || level === 'ERROR'
          ? 'bg-danger'
          : level === 'WARNING'
            ? 'bg-warning text-dark'
            : level === 'INFO'
              ? 'bg-info text-dark'
              : level === 'DEBUG'
                ? 'bg-success'
                : 'bg-secondary';

      return $('<tr>')
        .append($('<td>').text(number))
        .append($('<td>').text(it?.timestamp || ''))
        .append(
          $('<td>').append(
            $('<span>')
              .addClass(`badge ${badgeClass} text-uppercase fw-semibold`)
              .text(level || 'N/A')
          )
        )
        .append($('<td>').text(it?.logger || ''))
        .append(
          $('<td>')
            .text(it?.message || '')
        );
    });

    $tbody.append(rows);
  };

  const renderMeta = (data) => {
    const count = Number(data?.count || 0);
    const start = count ? state.offset + 1 : 0;
    const end = count ? Math.min(state.offset + state.limit, count) : 0;

    $('#display-range').text(`${start}-${end}`);
    $('#display-count').text(count);

    $('#prev-btn').prop('disabled', state.loading || state.offset <= 0);
    $('#next-btn').prop(
      'disabled',
      state.loading || state.offset + state.limit >= count
    );
  };

  const loadPage = async (offset = 0) => {
    if (state.loading) return;

    state.limit = getLimit();
    const requestId = ++state.requestId;
    state.loading = true;

    $('#search-btn, #prev-btn, #next-btn, #q-source').prop('disabled', true);

    try {
      const data = await fetchLogs(getParams(offset));
      if (!data || requestId !== state.requestId) return;

      state.offset = Number(data.offset ?? offset) || 0;
      renderRows(data.results || []);
      renderMeta(data);
    } finally {
      if (requestId === state.requestId) {
        state.loading = false;
        $('#search-btn, #q-source').prop('disabled', false);
        renderMeta({ count: Number($('#display-count').text() || 0) });
      }
    }
  };

  $('#search-btn').on('click', () => loadPage(0));
  $('#q-source').on('change', () => loadPage(0));
  $('#prev-btn').on('click', () =>
    loadPage(Math.max(0, state.offset - state.limit))
  );
  $('#next-btn').on('click', () =>
    loadPage(state.offset + state.limit)
  );
  $('#q-query').on('keydown', (e) => {
    if (e.key === 'Enter') loadPage(0);
  });

  $(loadPage.bind(null, 0));
})();
