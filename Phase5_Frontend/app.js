(function () {
  'use strict';

  var API_BASE = window.MF_FAQ_API_BASE || 'http://localhost:8000';
  var chatUrl = API_BASE.replace(/\/$/, '') + '/chat';

  // Disclaimer shown on every site launch; user must click "I understand" to proceed (no persistence)
  var disclaimerBanner = document.getElementById('disclaimer-banner');
  var disclaimerDismiss = document.getElementById('disclaimer-dismiss');
  if (disclaimerBanner && disclaimerDismiss) {
    disclaimerBanner.classList.remove('hidden');
    disclaimerDismiss.addEventListener('click', function () {
      disclaimerBanner.classList.add('hidden');
    });
  }

  var pageChat = document.getElementById('page-chat');
  var pageResources = document.getElementById('page-resources');
  var navHome = document.getElementById('nav-home');
  var navResources = document.getElementById('nav-resources');
  var resourcesList = document.getElementById('resources-list');
  var resourcesLoading = document.getElementById('resources-loading');
  var resourcesError = document.getElementById('resources-error');
  var resourcesLoaded = false;

  function showChat() {
    if (pageChat) pageChat.classList.remove('hidden');
    if (pageResources) pageResources.classList.add('hidden');
    if (navHome) navHome.setAttribute('aria-current', 'page');
    if (navResources) navResources.removeAttribute('aria-current');
  }

  var resourcesFundsByTypeWrap = document.getElementById('resources-funds-by-type-wrap');
  var resourcesFundsByTypeList = document.getElementById('resources-funds-by-type-list');
  var resourcesFundsLoaded = false;

  function renderFundsByType(byType) {
    if (!resourcesFundsByTypeList || !byType || Object.keys(byType).length === 0) return;
    var order = ['Equity', 'Hybrid', 'Index'];
    resourcesFundsByTypeList.innerHTML = '';
    order.forEach(function (typeLabel) {
      var funds = byType[typeLabel];
      if (!funds || funds.length === 0) return;
      var section = document.createElement('div');
      section.className = 'resources-fund-type-section';
      var heading = document.createElement('h3');
      heading.className = 'resources-fund-type-heading';
      heading.textContent = typeLabel;
      section.appendChild(heading);
      var ul = document.createElement('ul');
      ul.className = 'resources-fund-type-list';
      ul.setAttribute('aria-label', typeLabel + ' funds');
      funds.forEach(function (f) {
        var li = document.createElement('li');
        var schemeUrl = (f.scheme_page_url && String(f.scheme_page_url).trim()) ? f.scheme_page_url : null;
        var factsheetUrl = (f.factsheet_url && String(f.factsheet_url).trim()) ? f.factsheet_url : null;
        if (schemeUrl) {
          var nameA = document.createElement('a');
          nameA.href = schemeUrl;
          nameA.target = '_blank';
          nameA.rel = 'noopener noreferrer';
          nameA.textContent = f.fund_name || 'Fund';
          li.appendChild(nameA);
        } else {
          li.appendChild(document.createTextNode(f.fund_name || 'Fund'));
        }
        if (factsheetUrl) {
          var sep = document.createElement('span');
          sep.className = 'resources-fund-sep';
          sep.textContent = ' · ';
          li.appendChild(sep);
          var factsheetA = document.createElement('a');
          factsheetA.href = factsheetUrl;
          factsheetA.target = '_blank';
          factsheetA.rel = 'noopener noreferrer';
          factsheetA.className = 'resources-fund-link';
          factsheetA.textContent = 'Factsheet';
          li.appendChild(factsheetA);
        }
        ul.appendChild(li);
      });
      section.appendChild(ul);
      resourcesFundsByTypeList.appendChild(section);
    });
    if (resourcesFundsByTypeWrap) {
      resourcesFundsByTypeWrap.classList.remove('hidden');
    }
  }

  function showResources() {
    if (pageChat) pageChat.classList.add('hidden');
    if (pageResources) pageResources.classList.remove('hidden');
    if (navHome) navHome.removeAttribute('aria-current');
    if (navResources) navResources.setAttribute('aria-current', 'page');
    if (!resourcesLoaded && resourcesList && resourcesLoading) {
      var sourcesUrl = API_BASE.replace(/\/$/, '') + '/api/sources';
      fetch(sourcesUrl, { method: 'GET', cache: 'no-store' })
        .then(function (r) { return r.json(); })
        .then(function (items) {
          resourcesLoading.classList.add('hidden');
          if (!items || items.length === 0) {
            resourcesError.textContent = 'No source links available.';
            resourcesError.classList.remove('hidden');
            return;
          }
          resourcesList.innerHTML = '';
          items.forEach(function (item) {
            var li = document.createElement('li');
            var a = document.createElement('a');
            a.href = item.url || '#';
            a.target = '_blank';
            a.rel = 'noopener noreferrer';
            a.textContent = item.scheme_name || item.url || 'Link';
            var meta = document.createElement('span');
            meta.className = 'resource-meta';
            meta.textContent = (item.page_type || '') + (item.amc ? ' · ' + item.amc : '');
            li.appendChild(a);
            li.appendChild(meta);
            resourcesList.appendChild(li);
          });
          resourcesList.classList.remove('hidden');
          resourcesLoaded = true;
        })
        .catch(function () {
          resourcesLoading.classList.add('hidden');
          if (resourcesError) {
            resourcesError.textContent = 'Could not load source links. Try again later.';
            resourcesError.classList.remove('hidden');
          }
        });
    }
    if (!resourcesFundsLoaded && resourcesFundsByTypeList) {
      var fundsByTypeUrl = API_BASE.replace(/\/$/, '') + '/api/funds-by-type';
      fetch(fundsByTypeUrl, { method: 'GET', cache: 'no-store' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          resourcesFundsLoaded = true;
          if (data && data.by_type && Object.keys(data.by_type).length > 0) {
            renderFundsByType(data.by_type);
          }
        })
        .catch(function () { resourcesFundsLoaded = true; });
    }
  }

  if (navHome) {
    navHome.addEventListener('click', function (e) {
      e.preventDefault();
      showChat();
    });
  }
  if (navResources) {
    navResources.addEventListener('click', function (e) {
      e.preventDefault();
      showResources();
    });
  }

  var queryInput = document.getElementById('query-input');
  var sendBtn = document.getElementById('send-btn');
  var stopBtn = document.getElementById('stop-btn');
  var chatMessages = document.getElementById('chat-messages');
  var currentAbortController = null;
  var requestTimeoutId = null;
  var REQUEST_TIMEOUT_MS = 90000; // 90 seconds — RAG + Gemini can be slow; show error if backend is too slow
  var lastContextFund = ''; // fund name from last response, for follow-ups (e.g. "Expense ratio")

  function appendUserMessage(text) {
    var row = document.createElement('div');
    row.className = 'msg msg-user';
    row.setAttribute('data-role', 'user');
    row.innerHTML =
      '<span class="msg-avatar" aria-hidden="true">You</span>' +
      '<div class="msg-bubble">' + escapeHtml(text) + '</div>';
    chatMessages.appendChild(row);
    scrollToBottom();
  }

  function appendLoadingMessage() {
    var row = document.createElement('div');
    row.className = 'msg msg-bot msg-loading';
    row.setAttribute('data-role', 'bot');
    row.id = 'msg-loading';
    row.innerHTML =
      '<span class="msg-avatar" aria-hidden="true">MF</span>' +
      '<div class="msg-bubble">Sending your question…</div>';
    chatMessages.appendChild(row);
    scrollToBottom();
  }

  function removeLoadingMessage() {
    var el = document.getElementById('msg-loading');
    if (el) el.remove();
  }

  function appendBotMessage(data) {
    var rawAnswer = (data && data.answer) ? String(data.answer) : 'No answer returned.';
    var lastUpdatedMatch = rawAnswer.match(/\n?Last updated from sources:\s*([^\n.]+)\s*$/i);
    var answer = lastUpdatedMatch ? rawAnswer.replace(/\n?Last updated from sources:\s*[^\n.]+\.?\s*$/i, '').trim() : rawAnswer;
    var srcUrl = (data && data.source_url) ? String(data.source_url) : '';
    var refused = data && data.refused;

    var lastUpdatedHtml = lastUpdatedMatch
      ? '<div class="last-updated">Last updated from sources: ' + escapeHtml(lastUpdatedMatch[1].trim()) + '</div>'
      : '';

    var sourceHtml = srcUrl
      ? '<div class="source-row"><span class="source-label">Source:</span><a class="source-link" href="' + escapeAttr(srcUrl) + '" target="_blank" rel="noopener noreferrer">' + escapeHtml(srcUrl.length > 50 ? srcUrl.slice(0, 47) + '…' : srcUrl) + '</a></div>'
      : '';

    var refusedHtml = refused ? '<span class="refused-badge">Facts-only response — no advice given</span>' : '';

    var row = document.createElement('div');
    row.className = 'msg msg-bot';
    row.setAttribute('data-role', 'bot');
    row.innerHTML =
      '<span class="msg-avatar" aria-hidden="true">MF</span>' +
      '<div class="msg-bubble">' +
      '<div class="answer-text">' + escapeHtml(answer) + '</div>' +
      sourceHtml +
      lastUpdatedHtml +
      refusedHtml +
      '</div>';
    chatMessages.appendChild(row);
    scrollToBottom();
  }

  function appendBotErrorMessage(message) {
    var row = document.createElement('div');
    row.className = 'msg msg-bot';
    row.setAttribute('data-role', 'bot');
    row.innerHTML =
      '<span class="msg-avatar" aria-hidden="true">MF</span>' +
      '<div class="msg-bubble"><span class="msg-error">' + escapeHtml(message) + '</span></div>';
    chatMessages.appendChild(row);
    scrollToBottom();
  }

  function escapeHtml(s) {
    var div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
  }

  function escapeAttr(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function showLoading() {
    appendLoadingMessage();
    sendBtn.disabled = true;
    sendBtn.classList.add('hidden');
    stopBtn.classList.remove('hidden');
  }

  function hideLoadingState() {
    removeLoadingMessage();
    sendBtn.disabled = false;
    sendBtn.classList.remove('hidden');
    stopBtn.classList.add('hidden');
    currentAbortController = null;
  }

  function showError(message) {
    hideLoadingState();
    appendBotErrorMessage(message);
  }

  function showResult(data) {
    removeLoadingMessage();
    if (data.context_fund !== undefined) {
      lastContextFund = typeof data.context_fund === 'string' ? data.context_fund : '';
    }
    appendBotMessage(data);
    sendBtn.disabled = false;
    sendBtn.classList.remove('hidden');
    stopBtn.classList.add('hidden');
    currentAbortController = null;
    scrollToBottom();
  }

  function clearRequestTimeout() {
    if (requestTimeoutId) {
      clearTimeout(requestTimeoutId);
      requestTimeoutId = null;
    }
  }

  function stopRequest() {
    clearRequestTimeout();
    if (currentAbortController) {
      currentAbortController.abort();
    }
    removeLoadingMessage();
    sendBtn.disabled = false;
    sendBtn.classList.remove('hidden');
    stopBtn.classList.add('hidden');
    queryInput.value = '';
    currentAbortController = null;
  }

  function ask(query) {
    var q = (query || '').trim();
    if (!q) return;

    if (currentAbortController) {
      currentAbortController.abort();
    }
    clearRequestTimeout();

    appendUserMessage(q);
    queryInput.value = '';
    showLoading();

    var abortDueToTimeout = false;
    currentAbortController = new AbortController();
    var signal = currentAbortController.signal;

    requestTimeoutId = setTimeout(function () {
      requestTimeoutId = null;
      if (currentAbortController) {
        abortDueToTimeout = true;
        currentAbortController.abort();
      }
    }, REQUEST_TIMEOUT_MS);

    var body = { query: q };
    if (lastContextFund) body.context_fund = lastContextFund;
    fetch(chatUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: signal
    })
      .then(function (res) {
        clearRequestTimeout();
        return res.json().then(function (body) {
          if (!res.ok) {
            throw new Error(body.detail || res.statusText || 'Request failed');
          }
          return body;
        });
      })
      .then(showResult)
      .catch(function (err) {
        clearRequestTimeout();
        if (err.name === 'AbortError') {
          if (abortDueToTimeout) {
            removeLoadingMessage();
            sendBtn.disabled = false;
            sendBtn.classList.remove('hidden');
            stopBtn.classList.add('hidden');
            currentAbortController = null;
            appendBotErrorMessage('That took a bit long—please try again. You can use Stop to cancel a request.');
          } else {
            stopRequest();
          }
          return;
        }
        var msg = err.message || 'Failed to fetch';
        if (msg === 'Failed to fetch' || msg.indexOf('NetworkError') !== -1) {
          msg = 'Cannot reach the backend. From the project folder run: ./run_server.sh then open http://localhost:8000/ in your browser (one server, no separate backend).';
        }
        showError(msg);
      });
  }

  stopBtn.addEventListener('click', function () {
    stopRequest();
  });

  sendBtn.addEventListener('click', function () {
    ask(queryInput.value);
  });

  queryInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      ask(queryInput.value);
    }
  });

  document.querySelectorAll('.example-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var q = this.getAttribute('data-query') || '';
      queryInput.value = q;
      ask(q);
    });
  });

  var healthUrl = API_BASE.replace(/\/$/, '') + '/health';
  fetch(healthUrl, { method: 'GET', cache: 'no-store' })
    .catch(function () {
      appendBotErrorMessage('Backend not reachable. Run ./run_server.sh from the project folder, then open http://localhost:8000/ in your browser.');
    });
})();
