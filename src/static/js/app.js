/**
 * Course Recap Generator - Frontend Application Logic
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');
  const emptyState = document.getElementById('dropzone-empty-state');
  const selectedState = document.getElementById('file-selected-state');
  const selectedFilesBadge = document.getElementById('selected-files-badge');
  const selectedFilesTotalSize = document.getElementById('selected-files-total-size');
  const selectedFilesList = document.getElementById('selected-files-list');
  const btnAddMoreFiles = document.getElementById('btn-add-more-files');
  const btnClearAllFiles = document.getElementById('btn-clear-all-files');
  const btnGenerate = document.getElementById('btn-generate');
  const modelSelect = document.getElementById('model-select');

  // Progress Elements
  const progressSection = document.getElementById('progress-section');
  const progressDynamicStatus = document.getElementById('progress-dynamic-status');
  const elapsedTimer = document.getElementById('elapsed-timer');
  const step1 = document.getElementById('step-1');
  const step2 = document.getElementById('step-2');
  const step3 = document.getElementById('step-3');
  const step4 = document.getElementById('step-4');
  const divider1 = document.getElementById('divider-1');
  const divider2 = document.getElementById('divider-2');
  const divider3 = document.getElementById('divider-3');

  // Error Card
  const errorCard = document.getElementById('error-card');
  const errorMessage = document.getElementById('error-message');
  const btnCloseError = document.getElementById('btn-close-error');

  // Results Elements
  const resultsSection = document.getElementById('results-section');
  const courseTitleDisplay = document.getElementById('course-title-display');
  const resultFilenameDisplay = document.getElementById('result-filename-display');
  const metaTopicsCount = document.getElementById('meta-topics-count');
  const metaCharsCount = document.getElementById('meta-chars-count');
  const btnDownloadMarkdown = document.getElementById('btn-download-markdown');
  const btnCopyMarkdown = document.getElementById('btn-copy-markdown');

  // Tab View Elements
  const tabBtnStructured = document.getElementById('tab-btn-structured');
  const tabBtnMarkdown = document.getElementById('tab-btn-markdown');
  const tabBtnRaw = document.getElementById('tab-btn-raw');
  const viewStructured = document.getElementById('view-structured');
  const viewMarkdown = document.getElementById('view-markdown');
  const viewRaw = document.getElementById('view-raw');

  // Structured View Content
  const overviewCard = document.getElementById('overview-card');
  const overviewContent = document.getElementById('overview-content');
  const mermaidContainer = document.getElementById('mermaid-rendered-container');
  const diagramViewport = document.getElementById('diagram-viewport');
  const rawMermaidCode = document.getElementById('raw-mermaid-code');
  const diagramRawDrawer = document.getElementById('diagram-raw-drawer');
  const btnToggleMermaidCode = document.getElementById('btn-toggle-mermaid-code');
  const btnZoomIn = document.getElementById('btn-zoom-in');
  const btnZoomOut = document.getElementById('btn-zoom-out');
  const btnZoomReset = document.getElementById('btn-zoom-reset');
  const topicsContainer = document.getElementById('topics-container');

  // Alternate Tab Views
  const fullMarkdownPreview = document.getElementById('full-markdown-preview');
  const rawMarkdownContent = document.getElementById('raw-markdown-content');
  const rawSourceFilename = document.getElementById('raw-source-filename');

  // History & Toast
  const recentRecapsContainer = document.getElementById('recent-recaps-container');
  const recentPills = document.getElementById('recent-pills');
  const toastContainer = document.getElementById('toast-container');

  // Document Selection Tabs Elements
  const fileTabsBar = document.getElementById('file-tabs-bar');
  const fileTabsList = document.getElementById('file-tabs-list');
  const sourceFilenameBadge = document.getElementById('source-filename-badge');
  const sourceFilenameText = document.getElementById('source-filename-text');

  // State
  let selectedFiles = []; // Array of File objects
  let timerInterval = null;
  let startTime = 0;
  let allRecaps = []; // Array of independent recap objects
  let activeRecapIndex = 0;
  let currentRecapData = null;
  let currentZoom = 1.0;

  // Initialize Mermaid
  if (window.mermaid) {
    mermaid.initialize({
      startOnLoad: false,
      theme: 'default',
      securityLevel: 'loose',
      fontFamily: 'Inter, sans-serif',
      flowchart: {
        useMaxWidth: true,
        htmlLabels: true,
        curve: 'basis'
      }
    });
  }

  // Check health and load history on startup
  checkSystemHealth();
  loadRecapHistory();

  // Check URL parameters for direct recap loading (e.g. ?recap=astra1_recap.md)
  const urlParams = new URLSearchParams(window.location.search);
  const recapParam = urlParams.get('recap');
  if (recapParam) {
    loadExistingRecap(recapParam);
  }


  // ==========================================
  // File Upload & Drag-and-Drop Handlers
  // ==========================================

  dropzone.addEventListener('click', (e) => {
    if (
      (btnAddMoreFiles && btnAddMoreFiles.contains(e.target)) ||
      (btnClearAllFiles && btnClearAllFiles.contains(e.target)) ||
      (e.target.closest && e.target.closest('.btn-remove-single'))
    ) {
      return;
    }
    if (selectedFiles.length === 0) {
      fileInput.click();
    }
  });

  dropzone.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      if (e.target === dropzone && selectedFiles.length === 0) {
        e.preventDefault();
        fileInput.click();
      }
    }
  });

  if (btnAddMoreFiles) {
    btnAddMoreFiles.addEventListener('click', (e) => {
      e.stopPropagation();
      fileInput.click();
    });
  }

  if (btnClearAllFiles) {
    btnClearAllFiles.addEventListener('click', (e) => {
      e.stopPropagation();
      clearAllSelectedFiles();
    });
  }

  fileInput.addEventListener('change', () => {
    if (fileInput.files && fileInput.files.length > 0) {
      handleSelectedFiles(fileInput.files);
      fileInput.value = '';
    }
  });

  ['dragenter', 'dragover'].forEach(event => {
    dropzone.addEventListener(event, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add('drag-over');
    });
  });

  ['dragleave', 'drop'].forEach(event => {
    dropzone.addEventListener(event, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove('drag-over');
    });
  });

  dropzone.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleSelectedFiles(files);
    }
  });

  function handleSelectedFiles(filesList) {
    if (!filesList || filesList.length === 0) return;

    let addedCount = 0;
    let invalidCount = 0;

    Array.from(filesList).forEach(file => {
      const name = file.name.toLowerCase();
      if (!name.endsWith('.pdf') && !name.endsWith('.pptx') && !name.endsWith('.ppt')) {
        invalidCount++;
        return;
      }
      const exists = selectedFiles.some(f => f.name === file.name && f.size === file.size);
      if (!exists) {
        selectedFiles.push(file);
        addedCount++;
      }
    });

    if (invalidCount > 0) {
      showError(`Skipped ${invalidCount} unsupported file(s). Please upload course documents (.pdf).`);
    } else {
      hideError();
    }

    renderSelectedFiles();
  }

  function renderSelectedFiles() {
    if (selectedFiles.length === 0) {
      emptyState.style.display = 'block';
      selectedState.style.display = 'none';
      btnGenerate.disabled = true;
      return;
    }

    emptyState.style.display = 'none';
    selectedState.style.display = 'flex';
    btnGenerate.disabled = false;

    if (selectedFilesBadge) {
      selectedFilesBadge.textContent = `${selectedFiles.length} ${selectedFiles.length === 1 ? 'file' : 'files'} selected`;
    }

    const totalBytes = selectedFiles.reduce((acc, f) => acc + f.size, 0);
    if (selectedFilesTotalSize) {
      selectedFilesTotalSize.textContent = `${formatBytes(totalBytes)} total`;
    }

    if (selectedFilesList) {
      selectedFilesList.innerHTML = '';
      selectedFiles.forEach((file, index) => {
        const row = document.createElement('div');
        row.className = 'selected-file-row';

        const isPpt = file.name.toLowerCase().endsWith('.ppt') || file.name.toLowerCase().endsWith('.pptx');

        row.innerHTML = `
          <div class="selected-file-info">
            <div class="selected-file-icon" style="${isPpt ? 'background-color:#fed7aa; color:#ea580c;' : ''}">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
              </svg>
            </div>
            <div class="selected-file-meta">
              <span class="selected-file-title" title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</span>
              <span class="selected-file-sub">${formatBytes(file.size)}</span>
            </div>
          </div>
          <button type="button" class="btn-remove-single" data-index="${index}" title="Remove this file" aria-label="Remove ${escapeHtml(file.name)}">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        `;

        const removeBtn = row.querySelector('.btn-remove-single');
        removeBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          removeSelectedFile(index);
        });

        selectedFilesList.appendChild(row);
      });
    }
  }

  function removeSelectedFile(index) {
    if (index >= 0 && index < selectedFiles.length) {
      selectedFiles.splice(index, 1);
      renderSelectedFiles();
    }
  }

  function clearAllSelectedFiles() {
    selectedFiles = [];
    renderSelectedFiles();
  }

  function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  // ==========================================
  // Recap Generation Workflow
  // ==========================================

  btnGenerate.addEventListener('click', async () => {
    if (selectedFiles.length === 0) return;

    // Reset view
    hideError();
    resultsSection.style.display = 'none';
    progressSection.style.display = 'block';
    btnGenerate.disabled = true;

    // Start timer & stepper
    startTimer();
    const countMsg = selectedFiles.length === 1 ? 'course slides' : `${selectedFiles.length} course files`;
    updateStepper(1, `Invoking PDF Extraction MCP Server for ${countMsg}...`);

    // Progress simulation while server completes multi-agent pipeline
    const stepTimer1 = setTimeout(() => {
      updateStepper(2, 'Loading custom "course-recap" skill & curriculum guidelines...');
    }, 4500);

    const stepTimer2 = setTimeout(() => {
      updateStepper(3, 'Main Agent synthesizing combined topic breakdown and concept graph...');
    }, 9000);

    const stepTimer3 = setTimeout(() => {
      updateStepper(4, 'Sub-Agent "course-reviewer" auditing against source ground truth...');
    }, 16000);

    const formData = new FormData();
    selectedFiles.forEach(file => {
      formData.append('files', file);
    });
    // Single file backward compatibility
    formData.append('file', selectedFiles[0]);
    formData.append('model', modelSelect.value);

    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        body: formData,
      });

      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      clearTimeout(stepTimer3);

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Failed to generate recap.');
      }

      // Complete stepper
      markAllStepsComplete();
      progressDynamicStatus.textContent = 'Recap verified! Rendering visual diagrams...';

      setTimeout(async () => {
        stopTimer();
        progressSection.style.display = 'none';
        btnGenerate.disabled = false;
        await renderRecapData(data);
        showToast('Course recap generated successfully!');
        loadRecapHistory();
      }, 700);

    } catch (err) {
      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      clearTimeout(stepTimer3);
      stopTimer();
      progressSection.style.display = 'none';
      btnGenerate.disabled = false;
      showError(err.message || 'An error occurred during generation.');
    }
  });

  // ==========================================
  // Stepper & Progress Utilities
  // ==========================================

  function updateStepper(stepNum, statusText) {
    progressDynamicStatus.textContent = statusText;

    const steps = [step1, step2, step3, step4];
    const dividers = [divider1, divider2, divider3];

    steps.forEach((step, idx) => {
      const num = idx + 1;
      step.classList.remove('step-active', 'step-complete');
      if (num < stepNum) {
        step.classList.add('step-complete');
      } else if (num === stepNum) {
        step.classList.add('step-active');
      }
    });

    dividers.forEach((div, idx) => {
      if (idx + 1 < stepNum) {
        div.classList.add('step-divider-active');
      } else {
        div.classList.remove('step-divider-active');
      }
    });
  }

  function markAllStepsComplete() {
    [step1, step2, step3, step4].forEach(s => {
      s.classList.remove('step-active');
      s.classList.add('step-complete');
    });
    [divider1, divider2, divider3].forEach(d => {
      d.classList.add('step-divider-active');
    });
  }

  function startTimer() {
    startTime = Date.now();
    elapsedTimer.textContent = '00:00';
    if (timerInterval) clearInterval(timerInterval);
    timerInterval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      const mins = String(Math.floor(elapsed / 60)).padStart(2, '0');
      const secs = String(elapsed % 60).padStart(2, '0');
      elapsedTimer.textContent = `${mins}:${secs}`;
    }, 1000);
  }

  function stopTimer() {
    if (timerInterval) {
      clearInterval(timerInterval);
      timerInterval = null;
    }
  }

  // ==========================================
  // Rendering the Single Detailed Course Recap
  // ==========================================

  async function renderRecapData(data) {
    if (data.recaps && Array.isArray(data.recaps) && data.recaps.length > 0) {
      allRecaps = data.recaps;
    } else {
      allRecaps = [data];
    }

    activeRecapIndex = 0;

    // 1. Render file selector tabs if multiple files; hide if only 1 file
    renderFileTabs(allRecaps, activeRecapIndex);

    // 2. Render the single detailed recap viewer for the active file
    await displayActiveRecap(allRecaps[activeRecapIndex]);

    // Show single detailed results section
    resultsSection.style.display = 'flex';
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // Reset to default structured tab
    switchTab('structured');
  }

  function renderFileTabs(recaps, activeIndex) {
    if (!fileTabsBar || !fileTabsList) return;

    if (recaps.length <= 1) {
      fileTabsBar.style.display = 'none';
      return;
    }

    fileTabsBar.style.display = 'flex';
    fileTabsList.innerHTML = '';

    recaps.forEach((recap, idx) => {
      const tabBtn = document.createElement('button');
      tabBtn.type = 'button';
      tabBtn.className = `file-tab-btn ${idx === activeIndex ? 'file-tab-active' : ''}`;
      tabBtn.role = 'tab';
      tabBtn.setAttribute('aria-selected', idx === activeIndex ? 'true' : 'false');
      tabBtn.dataset.fileIndex = String(idx);
      tabBtn.dataset.filename = recap.filename || `file_${idx + 1}.pdf`;
      tabBtn.innerHTML = `
        <span class="file-tab-icon">📄</span>
        <span>${escapeHtml(recap.filename || `Document ${idx + 1}`)}</span>
      `;

      tabBtn.addEventListener('click', () => {
        selectActiveFile(idx);
      });

      fileTabsList.appendChild(tabBtn);
    });
  }

  async function selectActiveFile(idx) {
    if (!allRecaps || !allRecaps[idx]) return;
    activeRecapIndex = idx;

    // Update tab active classes
    if (fileTabsList) {
      const tabs = fileTabsList.querySelectorAll('.file-tab-btn');
      tabs.forEach((tab, i) => {
        if (i === idx) {
          tab.classList.add('file-tab-active');
          tab.setAttribute('aria-selected', 'true');
        } else {
          tab.classList.remove('file-tab-active');
          tab.setAttribute('aria-selected', 'false');
        }
      });
    }

    // Display ONLY this file's detailed recap
    await displayActiveRecap(allRecaps[idx]);
  }

  async function displayActiveRecap(recap) {
    currentRecapData = recap;

    // Source filename badge
    if (sourceFilenameText) {
      sourceFilenameText.textContent = recap.filename || 'course.pdf';
    }

    // Header info
    courseTitleDisplay.textContent = recap.title || 'Course Recap';
    resultFilenameDisplay.textContent = recap.output_filename || 'recap.md';
    metaTopicsCount.textContent = `${recap.topics ? recap.topics.length : 0} Topics`;
    metaCharsCount.textContent = `${(recap.markdown || '').length.toLocaleString()} Chars`;

    // 1. Course Overview (for THAT file only)
    if (recap.overview && recap.overview.trim()) {
      overviewContent.innerHTML = marked.parse(recap.overview);
      overviewCard.style.display = 'block';
    } else {
      overviewCard.style.display = 'none';
    }

    // 2. Render Mermaid Concept Diagram VISIBLY (for THAT file only)
    await renderMermaidDiagram(recap.mermaid);

    // 3. Render Topics Summary (from THAT specific file only)
    renderTopicsList(recap.topics);

    // 4. Render Alternate Views (for THAT specific file only)
    renderFullMarkdownView(recap.markdown);
    rawMarkdownContent.textContent = recap.markdown || '';
    rawSourceFilename.textContent = recap.output_filename || 'recap.md';
  }

  // ==========================================
  // Mermaid Visual Diagram Rendering
  // ==========================================

  async function renderMermaidDiagram(mermaidCode) {
    mermaidContainer.innerHTML = '';
    currentZoom = 1.0;
    applyDiagramZoom();

    if (!mermaidCode || !mermaidCode.trim()) {
      mermaidContainer.innerHTML = '<p class="text-muted" style="text-align:center; padding: 2rem;">No concept diagram found in recap.</p>';
      return;
    }

    // Clean code: remove any leading markdown markers if present
    let cleanCode = mermaidCode.trim();
    if (cleanCode.startsWith('```mermaid')) {
      cleanCode = cleanCode.replace(/^```mermaid\s*/, '').replace(/```$/, '').trim();
    }

    rawMermaidCode.textContent = cleanCode;

    if (!window.mermaid) {
      mermaidContainer.innerHTML = `<pre class="raw-code-block"><code>${escapeHtml(cleanCode)}</code></pre>`;
      return;
    }

    try {
      const renderId = 'mermaid-svg-' + Math.floor(Math.random() * 1000000);
      const { svg } = await mermaid.render(renderId, cleanCode);
      mermaidContainer.innerHTML = svg;
    } catch (renderError) {
      console.warn('Mermaid rendering warning:', renderError);
      // Attempt cleanup fallback (e.g. ensure flowchart TD)
      try {
        let fallbackCode = cleanCode;
        if (!fallbackCode.startsWith('flowchart') && !fallbackCode.startsWith('graph')) {
          fallbackCode = 'flowchart TD\n' + fallbackCode;
        }
        const fallbackId = 'mermaid-fallback-' + Math.floor(Math.random() * 1000000);
        const { svg } = await mermaid.render(fallbackId, fallbackCode);
        mermaidContainer.innerHTML = svg;
      } catch (finalErr) {
        mermaidContainer.innerHTML = `
          <div style="padding: 1.5rem; text-align: left; background: #fff5f5; border: 1px solid #fed7d7; border-radius: 8px; width: 100%;">
            <strong style="color: #c53030; display: block; margin-bottom: 0.5rem;">Visual Diagram Render Warning:</strong>
            <p style="font-size: 0.85rem; color: #742a2a; margin-bottom: 0.75rem;">${escapeHtml(finalErr.message)}</p>
            <pre class="raw-code-block" style="margin: 0;"><code>${escapeHtml(cleanCode)}</code></pre>
          </div>
        `;
      }
    }
  }

  // Diagram Zoom & Controls
  btnZoomIn.addEventListener('click', () => {
    if (currentZoom < 2.5) {
      currentZoom += 0.2;
      applyDiagramZoom();
    }
  });

  btnZoomOut.addEventListener('click', () => {
    if (currentZoom > 0.4) {
      currentZoom -= 0.2;
      applyDiagramZoom();
    }
  });

  btnZoomReset.addEventListener('click', () => {
    currentZoom = 1.0;
    applyDiagramZoom();
  });

  function applyDiagramZoom() {
    diagramViewport.style.transform = `scale(${currentZoom})`;
  }

  btnToggleMermaidCode.addEventListener('click', () => {
    if (diagramRawDrawer.style.display === 'none') {
      diagramRawDrawer.style.display = 'block';
      btnToggleMermaidCode.textContent = 'Hide Code';
    } else {
      diagramRawDrawer.style.display = 'none';
      btnToggleMermaidCode.textContent = 'View Code';
    }
  });

  // ==========================================
  // Topic-by-Topic Summary Cards
  // ==========================================

  function renderTopicsList(topics) {
    topicsContainer.innerHTML = '';
    if (!topics || topics.length === 0) {
      topicsContainer.innerHTML = '<p class="text-muted">No topic breakdowns available.</p>';
      return;
    }

    topics.forEach((topic) => {
      const card = document.createElement('article');
      card.className = 'topic-card';

      // Header
      const header = document.createElement('div');
      header.className = 'topic-card-header';
      header.innerHTML = `
        <span class="topic-badge">Topic ${topic.number || ''}</span>
        <h4 class="topic-card-title">${escapeHtml(topic.name || 'Topic')}</h4>
      `;
      card.appendChild(header);

      // Body
      const body = document.createElement('div');
      body.className = 'topic-card-body';

      if (topic.mechanisms || topic.definitions || topic.practical) {
        if (topic.mechanisms) {
          const b1 = document.createElement('div');
          b1.className = 'topic-subblock subblock-mechanisms';
          b1.innerHTML = `
            <div class="topic-subblock-title">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="16" x2="12" y2="12"/>
                <line x1="12" y1="8" x2="12.01" y2="8"/>
              </svg>
              Overview & Mechanisms
            </div>
            <div class="topic-subblock-content markdown-body">${marked.parse(topic.mechanisms)}</div>
          `;
          body.appendChild(b1);
        }

        if (topic.definitions) {
          const b2 = document.createElement('div');
          b2.className = 'topic-subblock subblock-definitions';
          b2.innerHTML = `
            <div class="topic-subblock-title">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z"/>
              </svg>
              Key Definitions & Principles
            </div>
            <div class="topic-subblock-content markdown-body">${marked.parse(topic.definitions)}</div>
          `;
          body.appendChild(b2);
        }

        if (topic.practical) {
          const b3 = document.createElement('div');
          b3.className = 'topic-subblock subblock-practical';
          b3.innerHTML = `
            <div class="topic-subblock-title">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
              </svg>
              Practical Implications
            </div>
            <div class="topic-subblock-content markdown-body">${marked.parse(topic.practical)}</div>
          `;
          body.appendChild(b3);
        }
      } else if (topic.raw_content) {
        const b = document.createElement('div');
        b.className = 'topic-subblock';
        b.innerHTML = `<div class="topic-subblock-content markdown-body">${marked.parse(topic.raw_content)}</div>`;
        body.appendChild(b);
      }

      card.appendChild(body);
      topicsContainer.appendChild(card);
    });
  }

  // ==========================================
  // Full Markdown Preview View
  // ==========================================

  async function renderFullMarkdownView(markdown) {
    if (!markdown) {
      fullMarkdownPreview.innerHTML = '';
      return;
    }

    // In full preview, replace mermaid code blocks with rendered containers
    const parts = markdown.split(/```mermaid\s*\n([\s\S]*?)```/);
    fullMarkdownPreview.innerHTML = '';

    for (let i = 0; i < parts.length; i++) {
      if (i % 2 === 0) {
        // Normal markdown text
        if (parts[i].trim()) {
          const textDiv = document.createElement('div');
          textDiv.innerHTML = marked.parse(parts[i]);
          fullMarkdownPreview.appendChild(textDiv);
        }
      } else {
        // Mermaid code part - render VISIBLE diagram!
        const diagramWrap = document.createElement('div');
        diagramWrap.className = 'diagram-canvas-container';
        diagramWrap.style.margin = '1.5rem 0';
        const innerContainer = document.createElement('div');
        innerContainer.className = 'mermaid-diagram-container';
        diagramWrap.appendChild(innerContainer);
        fullMarkdownPreview.appendChild(diagramWrap);

        const cleanMermaid = parts[i].trim();
        if (window.mermaid) {
          try {
            const mId = 'preview-mermaid-' + Math.floor(Math.random() * 1000000);
            const { svg } = await mermaid.render(mId, cleanMermaid);
            innerContainer.innerHTML = svg;
          } catch {
            innerContainer.innerHTML = `<pre class="raw-code-block"><code>${escapeHtml(cleanMermaid)}</code></pre>`;
          }
        }
      }
    }
  }

  // ==========================================
  // Tabs Navigation
  // ==========================================

  function switchTab(target) {
    [tabBtnStructured, tabBtnMarkdown, tabBtnRaw].forEach(b => b.classList.remove('tab-active'));
    [viewStructured, viewMarkdown, viewRaw].forEach(v => v.style.display = 'none');

    if (target === 'structured') {
      tabBtnStructured.classList.add('tab-active');
      viewStructured.style.display = 'block';
    } else if (target === 'markdown') {
      tabBtnMarkdown.classList.add('tab-active');
      viewMarkdown.style.display = 'block';
    } else if (target === 'raw') {
      tabBtnRaw.classList.add('tab-active');
      viewRaw.style.display = 'block';
    }
  }

  tabBtnStructured.addEventListener('click', () => switchTab('structured'));
  tabBtnMarkdown.addEventListener('click', () => switchTab('markdown'));
  tabBtnRaw.addEventListener('click', () => switchTab('raw'));

  // ==========================================
  // Download & Copy Handlers
  // ==========================================

  btnDownloadMarkdown.addEventListener('click', () => {
    if (!currentRecapData) return;
    const filename = currentRecapData.output_filename || 'recap.md';
    // Direct link to download route
    const link = document.createElement('a');
    link.href = `/api/download/${encodeURIComponent(filename)}`;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast(`Downloading ${filename}`);
  });

  btnCopyMarkdown.addEventListener('click', async () => {
    if (!currentRecapData || !currentRecapData.markdown) return;
    try {
      await navigator.clipboard.writeText(currentRecapData.markdown);
      showToast('Markdown copied to clipboard!');
    } catch {
      // Fallback
      const ta = document.createElement('textarea');
      ta.value = currentRecapData.markdown;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      showToast('Markdown copied to clipboard!');
    }
  });

  // ==========================================
  // History & Health
  // ==========================================

  async function checkSystemHealth() {
    try {
      const res = await fetch('/api/health');
      const data = await res.json();
      const statusText = document.getElementById('system-status-text');
      if (data.api_key_configured) {
        statusText.textContent = 'Gemini & MCP Ready';
      } else {
        statusText.textContent = 'API Key Missing';
        document.getElementById('system-badge').classList.add('badge-neutral');
      }
    } catch {
      // Ignore
    }
  }

  async function loadRecapHistory() {
    try {
      const res = await fetch('/api/history');
      const data = await res.json();
      if (data.recaps && data.recaps.length > 0) {
        recentPills.innerHTML = '';
        data.recaps.forEach(item => {
          const pill = document.createElement('button');
          pill.type = 'button';
          pill.className = 'recent-pill';
          pill.textContent = item.title || item.filename;
          pill.title = `Load ${item.filename}`;
          pill.addEventListener('click', async () => {
            await loadExistingRecap(item.filename);
          });
          recentPills.appendChild(pill);
        });
        recentRecapsContainer.style.display = 'flex';
      } else {
        recentRecapsContainer.style.display = 'none';
      }
    } catch {
      recentRecapsContainer.style.display = 'none';
    }
  }

  async function loadExistingRecap(filename) {
    try {
      hideError();
      const res = await fetch(`/api/recap/${encodeURIComponent(filename)}`);
      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.error || 'Failed to load recap.');
      }
      await renderRecapData(data);
      showToast(`Loaded ${data.title || filename}`);
    } catch (err) {
      showError(err.message || 'Failed to load recap.');
    }
  }

  // ==========================================
  // Toast & Error Utilities
  // ==========================================

  function showError(msg) {
    errorMessage.textContent = msg;
    errorCard.style.display = 'flex';
    errorCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function hideError() {
    errorCard.style.display = 'none';
  }

  btnCloseError.addEventListener('click', hideError);

  function showToast(msg) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = msg;
    toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
});
