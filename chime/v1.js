// ==UserScript==
// @name         Chime Control Button
// @namespace    http://tampermonkey.net/
// @version      2026-06-10
// @description  Show a Chime control box on the Chime login page
// @author       You
// @match        https://app.chime.com/login*
// @match        https://api.sardine.ai/*
// @icon         https://www.google.com/s2/favicons?sz=64&domain=chime.com
// @grant        none
// ==/UserScript==

(function () {
  'use strict';

  const buttonId = 'tm-chime-button';
  const panelId = 'tm-chime-panel';
  const storageKeys = [
    '@ChimeAnalytics:explatVariants',
    'CHIME-DEVICE-ID',
    'DEMO-DEVICE-ID',
    'chime-challenge-context',
    'chime-device-intelligence',
  ];
  const sardineStorageKey = '_immortal|deviceToken';
  const messageSource = 'tm-chime-control';
  let sardineDeviceToken = null;

  if (location.hostname === 'api.sardine.ai') {
    announceSardineToken();
    return;
  }

  window.addEventListener('message', (event) => {
    if (event.origin !== 'https://api.sardine.ai') return;
    if (event.data?.source !== messageSource || event.data?.type !== 'sardineDeviceToken') return;
    sardineDeviceToken = event.data.value;
  });

  function addStartButton() {
    if (document.getElementById(buttonId) || !document.body) return;

    const button = document.createElement('button');
    button.id = buttonId;
    button.type = 'button';
    button.textContent = 'Chime';
    button.setAttribute('aria-label', 'Open Chime controls');

    Object.assign(button.style, {
      position: 'fixed',
      right: '18px',
      bottom: '18px',
      zIndex: '999999',
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      minWidth: '112px',
      height: '44px',
      padding: '0 18px',
      backgroundColor: '#7357d8',
      color: '#ffffff',
      border: 'none',
      borderRadius: '999px',
      fontFamily: 'Arial, Helvetica, sans-serif',
      fontSize: '14px',
      fontWeight: '700',
      lineHeight: '1',
      cursor: 'pointer',
      boxShadow: '0 10px 22px rgba(42, 24, 117, 0.28)',
    });

    button.addEventListener('mouseenter', () => {
      button.style.backgroundColor = '#6247c8';
    });

    button.addEventListener('mouseleave', () => {
      button.style.backgroundColor = '#7357d8';
    });

    button.addEventListener('click', () => {
      openPanel();
    });

    document.body.appendChild(button);
  }

  function openPanel() {
    if (document.getElementById(panelId)) return;

    const panel = document.createElement('div');
    panel.id = panelId;

    const header = document.createElement('div');
    const title = document.createElement('strong');
    const closeButton = document.createElement('button');

    title.textContent = 'Chime';
    closeButton.type = 'button';
    closeButton.textContent = 'x';
    closeButton.setAttribute('aria-label', 'Close Chime controls');

    header.append(title, closeButton);

    const status = document.createElement('div');
    status.textContent = 'NOT STARTED';

    const log = document.createElement('div');
    log.textContent = 'Ready to start';

    const startButton = document.createElement('button');
    startButton.type = 'button';
    startButton.textContent = 'START';

    panel.append(header, status, log, startButton);

    Object.assign(panel.style, {
      position: 'fixed',
      right: '18px',
      bottom: '76px',
      width: '360px',
      maxWidth: 'calc(100vw - 36px)',
      zIndex: '1000000',
      backgroundColor: '#f1f2f4',
      borderRadius: '8px',
      overflow: 'hidden',
      boxShadow: '0 16px 34px rgba(0, 0, 0, 0.28)',
      fontFamily: 'Arial, Helvetica, sans-serif',
      color: '#263238',
    });

    Object.assign(header.style, {
      height: '56px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      position: 'relative',
      backgroundColor: '#7357d8',
      color: '#ffffff',
      fontSize: '16px',
    });

    Object.assign(closeButton.style, {
      position: 'absolute',
      right: '10px',
      top: '10px',
      width: '34px',
      height: '34px',
      border: 'none',
      borderRadius: '999px',
      backgroundColor: 'rgba(255, 255, 255, 0.22)',
      color: '#ffffff',
      fontSize: '18px',
      fontWeight: '700',
      cursor: 'pointer',
      lineHeight: '1',
    });

    Object.assign(status.style, {
      margin: '14px 8px 10px',
      padding: '12px',
      borderRadius: '7px',
      backgroundColor: '#ffffff',
      color: '#7357d8',
      textAlign: 'center',
      fontSize: '13px',
      fontWeight: '700',
    });

    Object.assign(log.style, {
      margin: '0 8px 10px',
      padding: '11px 12px',
      borderRadius: '7px',
      backgroundColor: '#ffffff',
      color: '#69727a',
      textAlign: 'center',
      fontSize: '12px',
    });

    Object.assign(startButton.style, {
      display: 'block',
      width: 'calc(100% - 16px)',
      height: '44px',
      margin: '0 8px 14px',
      border: 'none',
      borderRadius: '7px',
      backgroundColor: '#6f72e8',
      color: '#ffffff',
      fontSize: '13px',
      fontWeight: '700',
      cursor: 'pointer',
    });

    closeButton.addEventListener('click', () => {
      panel.remove();
    });

    startButton.addEventListener('click', () => {
      const values = readStorageValues();

      status.textContent = 'STARTED';
      log.textContent = `Started at ${new Date().toLocaleTimeString()}`;
      printStorageValues(values);
    });

    document.body.appendChild(panel);
  }

  function readStorageValues() {
    const values = storageKeys.reduce((result, key) => {
      result[key] = readBrowserValue(key).value;
      return result;
    }, {});

    values[sardineStorageKey] = sardineDeviceToken;
    return values;
  }

  function printStorageValues(values) {
    const details = {};

    console.group('Chime browser storage values');
    storageKeys.forEach((key) => {
      details[key] = readBrowserValue(key);
      console.log(`${key}:`, values[key]);
      console.log(`${key} source:`, details[key].source);
    });
    console.log(`${sardineStorageKey}:`, values[sardineStorageKey]);
    details[sardineStorageKey] = {
      source: values[sardineStorageKey] ? 'https://api.sardine.ai localStorage' : 'not found',
      value: values[sardineStorageKey],
    };
    console.table(values);
    console.table(details);
    console.groupEnd();
  }

  function readBrowserValue(key) {
    const localValue = localStorage.getItem(key);
    if (localValue !== null) return { source: 'localStorage', value: localValue };

    const sessionValue = sessionStorage.getItem(key);
    if (sessionValue !== null) return { source: 'sessionStorage', value: sessionValue };

    const cookieValue = readCookie(key);
    if (cookieValue !== null) return { source: 'cookie', value: cookieValue };

    const localFuzzyValue = findStorageValue(localStorage, key);
    if (localFuzzyValue) return localFuzzyValue;

    const sessionFuzzyValue = findStorageValue(sessionStorage, key);
    if (sessionFuzzyValue) return sessionFuzzyValue;

    return { source: 'not found', value: null };
  }

  function findStorageValue(storage, searchKey) {
    const wanted = searchKey.toLowerCase();

    for (let index = 0; index < storage.length; index += 1) {
      const key = storage.key(index);
      if (!key || key.toLowerCase() !== wanted) continue;
      return { source: `${storage === localStorage ? 'localStorage' : 'sessionStorage'}:${key}`, value: storage.getItem(key) };
    }

    for (let index = 0; index < storage.length; index += 1) {
      const key = storage.key(index);
      if (!key || !key.toLowerCase().includes(wanted)) continue;
      return { source: `${storage === localStorage ? 'localStorage' : 'sessionStorage'}:${key}`, value: storage.getItem(key) };
    }

    return null;
  }

  function readCookie(name) {
    const cookies = document.cookie ? document.cookie.split('; ') : [];
    const cookie = cookies.find((item) => item.startsWith(`${encodeURIComponent(name)}=`) || item.startsWith(`${name}=`));
    if (!cookie) return null;
    return decodeURIComponent(cookie.slice(cookie.indexOf('=') + 1));
  }

  function announceSardineToken() {
    const sendToken = () => {
      window.top.postMessage(
        {
          source: messageSource,
          type: 'sardineDeviceToken',
          value: localStorage.getItem(sardineStorageKey),
        },
        'https://app.chime.com'
      );
    };

    sendToken();
    let attempts = 0;
    const timer = setInterval(() => {
      attempts += 1;
      sendToken();
      if (attempts >= 10) clearInterval(timer);
    }, 1000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', addStartButton, { once: true });
  } else {
    addStartButton();
  }
})();
