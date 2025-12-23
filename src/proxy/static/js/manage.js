// Modal handling for Add / Edit Node
const modal = document.getElementById('node-modal');
const modalTitle = document.getElementById('modal-title');
const modalForm = document.getElementById('modal-form');
const modalNodeId = document.getElementById('modal-node-id');
const modalAction = document.getElementById('modal-action');
const modalName = document.getElementById('modal-name');
const modalAddress = document.getElementById('modal-address');
const modalPort = document.getElementById('modal-port');
const openAddBtn = document.getElementById('open-add-node');
const closeBtn = document.getElementById('modal-close');

function openModal(mode, data) {
  modal.style.display = 'flex';
  modal.setAttribute('aria-hidden', 'false');
  if (mode === 'add') {
    modalTitle.textContent = 'Add Node';
    modalAction.value = 'add_node';
    modalNodeId.value = '';
    modalName.value = '';
    modalAddress.value = '';
    modalPort.value = '';
  } else {
    modalTitle.textContent = 'Edit Node';
    modalAction.value = 'edit_node';
    modalNodeId.value = data.id || '';
    modalName.value = data.name || '';
    modalAddress.value = data.address || '';
    modalPort.value = data.port || '';
  }
}

function closeModal() {
  modal.style.display = 'none';
  modal.setAttribute('aria-hidden', 'true');
}

document.querySelectorAll('.edit-node-btn').forEach(btn => {
  btn.addEventListener('click', (e) => {
    const id = btn.getAttribute('data-id');
    const name = btn.getAttribute('data-name');
    const address = btn.getAttribute('data-address');
    const port = btn.getAttribute('data-port');
    openModal('edit', { id, name, address, port });
  });
});

openAddBtn.addEventListener('click', () => openModal('add', {}));
closeBtn.addEventListener('click', closeModal);
window.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });

const detailsModal = document.getElementById('details-modal');
const detailsModalClose = document.getElementById('details-modal-close');
const detailsContent = document.getElementById('details-content');

async function fetchNodeDetails(nodeId) {
  try {
    const res = await fetch(`/api/proxy/active-requests?node_id=${nodeId}`, { credentials: 'same-origin' });
    if (!res.ok) { throw new Error('status ' + res.status); }
    const data = await res.json();
    return data.nodes && data.nodes.length > 0 ? data.nodes[0] : null;
  } catch (e) {
    console.error('fetchNodeDetails error', e);
    return null;
  }
}

function renderNodeDetails(nodeData) {
  if (!nodeData) {
    detailsContent.innerHTML = '<div class="details-error">Failed to load node details</div>';
    return;
  }

  const latencyText = nodeData.latency !== null && nodeData.latency !== undefined
    ? (nodeData.latency * 1000).toFixed(2) + ' ms'
    : 'N/A';

  const modelsHtml = nodeData.models && nodeData.models.length > 0
    ? nodeData.models.map(m => `<li>${m}</li>`).join('')
    : '<li>No models available</li>';

  detailsContent.innerHTML = `
    <div class="details-section">
      <div class="details-row"><span class="details-label">ID:</span><span class="details-value">${nodeData.id}</span></div>
      <div class="details-row"><span class="details-label">Name:</span><span class="details-value">${nodeData.name}</span></div>
      <div class="details-row"><span class="details-label">Address:</span><span class="details-value">${nodeData.address}</span></div>
      <div class="details-row"><span class="details-label">Status:</span><span class="details-value status-${nodeData.status}">${nodeData.status.toUpperCase()}</span></div>
      <div class="details-row"><span class="details-label">Active Requests:</span><span class="details-value">${nodeData.active_requests}</span></div>
      <div class="details-row"><span class="details-label">Latency:</span><span class="details-value">${latencyText}</span></div>
      <div class="details-row"><span class="details-label">Available Models (${nodeData.models ? nodeData.models.length : 0}):</span></div>
      <ul class="details-models">${modelsHtml}</ul>
    </div>
  `;
}

function openDetailsModal(nodeId) {
  detailsModal.style.display = 'flex';
  detailsModal.setAttribute('aria-hidden', 'false');
  detailsContent.innerHTML = '<div class="details-loading">Loading...</div>';
  fetchNodeDetails(nodeId).then(data => renderNodeDetails(data));
}

function closeDetailsModal() {
  detailsModal.style.display = 'none';
  detailsModal.setAttribute('aria-hidden', 'true');
}

document.querySelectorAll('.details-node-btn').forEach(btn => {
  btn.addEventListener('click', (e) => openDetailsModal(btn.getAttribute('data-id')));
});

detailsModalClose.addEventListener('click', closeDetailsModal);
window.addEventListener('click', (e) => { if (e.target === detailsModal) closeDetailsModal(); });

const pullModal = document.getElementById('pull-modal');
const pullModalClose = document.getElementById('pull-modal-close');
const pullModalTitle = document.getElementById('pull-modal-title');
const pullModelInput = document.getElementById('pull-model-input');
const pullSubmitBtn = document.getElementById('pull-submit');
const pullStatus = document.getElementById('pull-status');
const pullNodeInfo = document.getElementById('pull-node-info');
let currentPullNodeId = null;
let currentPullNodeName = null;

async function fetchNodeInfo(nodeId) {
  try {
    const res = await fetch(`/api/proxy/active-requests?node_id=${nodeId}`, { credentials: 'same-origin' });
    if (!res.ok) { throw new Error('status ' + res.status); }
    const data = await res.json();
    return data.nodes && data.nodes.length > 0 ? data.nodes[0] : null;
  } catch (e) {
    console.error('fetchNodeInfo error', e);
    return null;
  }
}

function renderPullNodeInfo(nodeData) {
  if (!nodeData) {
    pullNodeInfo.innerHTML = '<div class="pull-info-error">Failed to load node information</div>';
    return;
  }

  const modelsCount = nodeData.models ? nodeData.models.length : 0;
  const modelsHtml = nodeData.models && nodeData.models.length > 0
    ? nodeData.models.map(m => `<li>${m}</li>`).join('')
    : '<li style="color:#999">No models installed</li>';

  pullNodeInfo.innerHTML = `
    <div class="pull-info-section">
      <div class="pull-info-header">
        <strong>Current Models on ${nodeData.name} (${modelsCount})</strong>
      </div>
      <ul class="pull-models-list">${modelsHtml}</ul>
    </div>
  `;
}

function openPullModal(nodeId, nodeName) {
  currentPullNodeId = nodeId;
  currentPullNodeName = nodeName;
  pullModal.style.display = 'flex';
  pullModal.setAttribute('aria-hidden', 'false');
  pullModalTitle.textContent = `Pull Model to ${nodeName}`;
  pullModelInput.value = '';
  pullStatus.style.display = 'none';
  pullSubmitBtn.disabled = false;
  pullNodeInfo.innerHTML = '<div class="pull-info-loading">Loading node information...</div>';
  fetchNodeInfo(nodeId).then(data => renderPullNodeInfo(data));
}

function closePullModal() {
  pullModal.style.display = 'none';
  pullModal.setAttribute('aria-hidden', 'true');
  currentPullNodeId = null;
  currentPullNodeName = null;
}

async function pullModelToNode() {
  const modelName = pullModelInput.value.trim();
  if (!modelName) {
    pullStatus.style.display = 'block';
    pullStatus.className = 'pull-status pull-error';
    pullStatus.textContent = 'Please enter a model name';
    return;
  }

  pullSubmitBtn.disabled = true;
  pullStatus.style.display = 'block';
  pullStatus.className = 'pull-status pull-loading';
  pullStatus.textContent = 'Pulling model... This may take a few minutes.';

  try {
    const response = await fetch('/api/proxy/pull', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
      },
      credentials: 'same-origin',
      body: JSON.stringify({ model: modelName, node_id: currentPullNodeId })
    });

    const data = await response.json();

    if (response.ok && data.results && data.results.length > 0) {
      const result = data.results[0];
      if (result.status === 'success') {
        pullStatus.className = 'pull-status pull-success';
        pullStatus.textContent = `✓ ${result.message}`;
        setTimeout(() => closePullModal(), 2000);
      } else {
        pullStatus.className = 'pull-status pull-error';
        pullStatus.textContent = `✗ ${result.message}`;
        pullSubmitBtn.disabled = false;
      }
    } else {
      pullStatus.className = 'pull-status pull-error';
      pullStatus.textContent = `✗ ${data.error || 'Failed to pull model'}`;
      pullSubmitBtn.disabled = false;
    }
  } catch (error) {
    pullStatus.className = 'pull-status pull-error';
    pullStatus.textContent = `✗ Error: ${error.message}`;
    pullSubmitBtn.disabled = false;
  }
}

document.querySelectorAll('.pull-node-btn').forEach(btn => {
  btn.addEventListener('click', () => openPullModal(btn.getAttribute('data-id'), btn.getAttribute('data-name')));
});

pullSubmitBtn.addEventListener('click', pullModelToNode);
pullModalClose.addEventListener('click', closePullModal);
window.addEventListener('click', (e) => { if (e.target === pullModal) closePullModal(); });

pullModelInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter' && !pullSubmitBtn.disabled) {
    pullModelToNode();
  }
});

async function fetchModels() {
  try {
    const res = await fetch('/api/proxy/tags', { credentials: 'same-origin' });
    if (!res.ok) { throw new Error('status ' + res.status); }
    const data = await res.json();
    return data.models || [];
  } catch (e) {
    console.error('fetchModels error', e);
    return [];
  }
}

function renderModels(models) {
  const modelsList = document.getElementById('models-list');
  const modelCount = document.getElementById('model-count');

  if (!Array.isArray(models) || models.length === 0) {
    modelCount.textContent = '0';
    modelsList.innerHTML = '<div class="loading-text">No models available</div>';
    return;
  }

  modelCount.textContent = models.length;

  const sortedModels = models.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
  modelsList.innerHTML = sortedModels.map(model => `<div class="model-item">${model.name || ''}</div>`).join('');
}

document.getElementById('refresh-models').addEventListener('click', async () => {
  document.getElementById('models-list').innerHTML = '<div class="loading-text">Loading...</div>';
  document.getElementById('model-count').textContent = '...';
  renderModels(await fetchModels());
});

(async () => { renderModels(await fetchModels()); })();

async function fetchAllNodesStatus() {
  try {
    const res = await fetch('/api/proxy/active-requests', { credentials: 'same-origin' });
    if (!res.ok) { throw new Error('status ' + res.status); }
    const data = await res.json();
    return data.nodes || [];
  } catch (e) {
    console.error('fetchAllNodesStatus error', e);
    return [];
  }
}

function renderNodesPreview(nodes) {
  const previewDiv = document.getElementById('nodes-preview');

  if (!nodes || nodes.length === 0) {
    previewDiv.innerHTML = '<div class="preview-error">No active nodes available</div>';
    previewDiv.style.display = 'block';
    return;
  }

  previewDiv.innerHTML = nodes.map(node => `
    <div class="node-preview-card">
      <div class="node-preview-header">
        <strong>${node.name}</strong>
        <span class="${node.status === 'active' ? 'status-active' : 'status-standby'}">${node.status}</span>
      </div>
      <div class="node-preview-info">
        <div>Models: ${node.models ? node.models.length : 0}</div>
        <div class="node-preview-models">
          ${node.models && node.models.length > 0 ? node.models.slice(0, 3).join(', ') + (node.models.length > 3 ? '...' : '') : 'No models'}
        </div>
      </div>
    </div>
  `).join('');
  previewDiv.style.display = 'block';
}

document.getElementById('show-nodes-preview').addEventListener('click', async () => {
  const previewDiv = document.getElementById('nodes-preview');
  previewDiv.innerHTML = '<div class="loading-text">Loading nodes status...</div>';
  previewDiv.style.display = 'block';
  renderNodesPreview(await fetchAllNodesStatus());
});

document.getElementById('pull-all-submit').addEventListener('click', async () => {
  const modelName = document.getElementById('pull-all-model-input').value.trim();
  const statusDiv = document.getElementById('pull-all-status');
  const submitBtn = document.getElementById('pull-all-submit');

  if (!modelName) {
    statusDiv.style.display = 'block';
    statusDiv.className = 'pull-status pull-error';
    statusDiv.textContent = 'Please enter a model name';
    return;
  }

  submitBtn.disabled = true;
  statusDiv.style.display = 'block';
  statusDiv.className = 'pull-status pull-loading';
  statusDiv.textContent = 'Pulling model to all nodes... This may take several minutes.';

  try {
    const response = await fetch('/api/proxy/pull', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
      },
      credentials: 'same-origin',
      body: JSON.stringify({ model: modelName })
    });

    const data = await response.json();

    if (response.ok && data.results) {
      const successCount = data.results.filter(r => r.status === 'success').length;
      const totalCount = data.results.length;

      statusDiv.className = successCount === totalCount ? 'pull-status pull-success' : 'pull-status pull-error';
      statusDiv.textContent = successCount === totalCount
        ? `✓ Successfully pulled to all ${totalCount} nodes`
        : `⚠ Pulled to ${successCount}/${totalCount} nodes. Some failed.`;

      statusDiv.innerHTML += `<div class="pull-results-detail">${data.results.map(r =>
        `<div class="pull-result ${r.status === 'success' ? 'success' : 'error'}">${r.node_name}: ${r.message}</div>`
      ).join('')}</div>`;

      submitBtn.disabled = false;
    } else {
      statusDiv.className = 'pull-status pull-error';
      statusDiv.textContent = `✗ ${data.error || 'Failed to pull model'}`;
      submitBtn.disabled = false;
    }
  } catch (error) {
    statusDiv.className = 'pull-status pull-error';
    statusDiv.textContent = `✗ Error: ${error.message}`;
    submitBtn.disabled = false;
  }
});
