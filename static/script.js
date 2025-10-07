/* ────────────────────────────────────────────────────────────
   PEN.ai Chatbot – self-injecting backup (bubble + consent UI)
   - Injects minimal HTML + styles if missing
   - Fetch shim to hit chatbot origin across services
   - Preserves existing behaviour and labels
   - FIXED: Emily greeting bubble with better positioning and triggers
───────────────────────────────────────────────────────────── */

console.log("✅ PEN.ai self-injecting script.js loaded");

// === 0) Config: set your chatbot backend origin here (or window.PENAI_CHATBOT_ORIGIN) ===
const CHATBOT_ORIGIN = window.PENAI_CHATBOT_ORIGIN || "http://localhost:5001";

// === Extract family_id from URL or localStorage (PERSISTENT) ===
let FAMILY_ID = new URLSearchParams(window.location.search).get('family_id');

// If found in URL, save to localStorage for persistence
if (FAMILY_ID) {
  try {
    localStorage.setItem('emily_family_id', FAMILY_ID);
    console.log('✅ Family ID saved to localStorage:', FAMILY_ID);
  } catch (e) {
    console.error('Failed to save family_id:', e);
  }
}

// If not in URL, try localStorage (persistent across sessions)
if (!FAMILY_ID) {
  try {
    FAMILY_ID = localStorage.getItem('emily_family_id');
    if (FAMILY_ID) {
      console.log('✅ Family ID from localStorage:', FAMILY_ID);
    } else {
      // Fallback to old enquiryData format
      const stored = localStorage.getItem('enquiryData');
      if (stored) {
        const data = JSON.parse(stored);
        FAMILY_ID = data.id;
        // Migrate to new format
        localStorage.setItem('emily_family_id', FAMILY_ID);
        console.log('✅ Family ID migrated from enquiryData:', FAMILY_ID);
      }
    }
  } catch (e) {
    console.error('Failed to parse stored data:', e);
  }
}

if (FAMILY_ID) {
  console.log('✅ Family ID loaded:', FAMILY_ID);
  
  // Initialize backend session with family_id
  fetch('/api/family/init', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    credentials: 'include',
    body: JSON.stringify({family_id: FAMILY_ID})
  }).catch(e => console.log('Could not init family session:', e));
} else {
  console.log('⚠️ No family ID found');
}

// === 1) Fetch shim: route same-origin paths to chatbot backend when site + bot are separate ===
(function () {
  const origFetch = window.fetch.bind(window);
  window.fetch = (input, init) => {
    if (typeof input === "string" && input.startsWith("/")) input = CHATBOT_ORIGIN + input;
    return origFetch(input, init);
  };
})();

// === 2) Inject minimal styles once (only if not already present) ===
(function ensureStyles() {
  if (document.getElementById("penai-styles")) return;
  const css = `
  :root { --primary-color:#091825; --accent-color:#FF9F1C; --text-color:#fff; --chat-bg:#f9f9f9; --border-color:#e0e0e0; --button-bg:#f0f0f0; --button-fg:#444; }
  #penai-toggle{position:fixed;bottom:20px;right:20px;width:60px;height:60px;border-radius:50%;background:var(--accent-color);color:#fff;font-size:28px;display:flex;align-items:center;justify-content:center;cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,.2);z-index:100000;transition:transform .2s ease;}
  #penai-toggle:hover{background:#e98f14;transform:scale(1.05);}
  #penai-chatbox{display:none;flex-direction:column;position:fixed;bottom:90px;right:20px;width:360px;max-height:600px;background:#fff;border:1px solid var(--border-color);border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,.15);z-index:100000;overflow:hidden;}
  #penai-chatbox.open{display:flex;animation:penai-slideUp .25s ease-out;}
  @keyframes penai-slideUp{from{transform:translateY(16px);opacity:0}to{transform:translateY(0);opacity:1}}
  #penai-header{display:flex;align-items:center;gap:8px;padding:10px 12px;background:var(--primary-color);color:#fff;}
  #penai-header h2{margin:0;font-size:16px;flex:1;}
  #penai-close{background:none;border:none;color:#fff;font-size:18px;cursor:pointer;line-height:1;padding:4px 6px;border-radius:6px;}
  #penai-close:hover{background-color:rgba(255,255,255,.12);}
  #language-selector{font-size:12px;padding:3px 6px;border-radius:4px;border:1px solid #ccc;background:#fff;color:#000;}
  .penai-ctl{padding:6px 10px;background:var(--button-bg);color:var(--button-fg);font-size:12px;border-radius:6px;border:1px solid #ccc;cursor:pointer;}
  .penai-ctl.hidden{display:none!important;}
  #welcome-message{padding:10px 15px;background:#f9f9f9;color:#091825;font-size:14px;}
  #chat-history{flex:1;padding:15px 15px 100px;overflow-y:auto;background:var(--chat-bg);border-top:1px solid var(--border-color);border-bottom:1px solid var(--border-color);scroll-behavior:smooth;}
  .message{margin-bottom:12px;padding:10px;font-size:14px;line-height:1.4;max-width:85%;word-wrap:break-word;border:1px solid #e0e0e0;border-radius:8px;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.05);}
  .message.user{text-align:right;align-self:flex-end;color:#333;}
  .message.bot{text-align:left;align-self:flex-start;color:#091825;}
  .message.bot p::before{content:"Emily: ";font-weight:700;}
  .chat-link{display:block;margin-top:5px;text-decoration:underline;font-size:14px;color:#0056b3;}
  #button-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;padding:10px;background:#f1f1f1;border-top:1px solid #ddd;border-bottom:1px solid #ddd;}
  .quick-reply{padding:6px 8px;background:var(--button-bg);color:var(--button-fg);font-size:12px;border-radius:20px;border:1px solid #ccc;cursor:pointer;}
  .quick-reply:hover{background:#e0e0e0;}
  #penai-input-container{display:flex;padding:10px;background:#fff;}
  #question-input{flex:1;padding:8px;border:1px solid var(--border-color);border-radius:5px;font-size:14px;}
  #send-button{margin-left:8px;padding:8px 12px;background:var(--primary-color);color:#fff;border:none;border-radius:5px;font-size:14px;cursor:pointer;}
  #send-button:hover{background-color:#0c2235;}
  #thinking-text{padding:10px 15px;display:none;font-style:italic;color:#777;}
  #thinking-text::after{content:"";display:inline-block;width:1em;text-align:left;animation:penai-dots 1.2s steps(3,end) infinite;}
  @keyframes penai-dots{0%{content:""}33%{content:"."}66%{content:".."}100%{content:"..."}}
  .voice-indicator.hidden{display:none!important;}
  
  /* FIXED: Emily greeting bubble with mobile support */
  #emily-greeting-bubble{
    position:fixed;
    bottom:100px;
    right:20px;
    max-width:300px;
    background:#fff;
    border:2px solid var(--accent-color);
    border-radius:16px;
    padding:18px 22px 18px 18px;
    box-shadow:0 8px 32px rgba(0,0,0,.25);
    z-index:100001;
    opacity:0;
    transform:translateY(20px) scale(0.95);
    transition:opacity .5s ease, transform .5s ease;
    pointer-events:none;
    display:none;
    -webkit-tap-highlight-color:transparent;
    cursor:pointer;
  }
  #emily-greeting-bubble.show{
    opacity:1;
    transform:translateY(0) scale(1);
    pointer-events:auto;
    display:block;
  }
  #emily-greeting-bubble::after{
    content:"";
    position:absolute;
    bottom:-12px;
    right:28px;
    width:0;
    height:0;
    border-left:12px solid transparent;
    border-right:12px solid transparent;
    border-top:12px solid var(--accent-color);
  }
  #emily-greeting-bubble p{
    margin:0;
    color:var(--primary-color);
    font-size:14px;
    line-height:1.6;
    padding-right:20px;
  }
  #emily-greeting-bubble .close-bubble{
    position:absolute;
    top:8px;
    right:8px;
    background:none;
    border:none;
    color:#999;
    font-size:20px;
    cursor:pointer;
    width:24px;
    height:24px;
    display:flex;
    align-items:center;
    justify-content:center;
    border-radius:50%;
    transition:background .2s, color .2s;
    line-height:1;
    -webkit-tap-highlight-color:transparent;
  }
  #emily-greeting-bubble .close-bubble:hover{
    background:#f0f0f0;
    color:#333;
  }
  #emily-greeting-bubble .close-bubble:active{
    background:#e0e0e0;
  }
  
  /* Mobile optimizations */
  @media (max-width: 768px) {
    #emily-greeting-bubble{
      bottom:90px;
      right:10px;
      left:10px;
      max-width:calc(100% - 20px);
      margin:0 auto;
    }
    #emily-greeting-bubble::after{
      right:20px;
    }
    #penai-chatbox{
      bottom:80px;
      right:10px;
      left:10px;
      width:calc(100% - 20px);
      max-width:none;
    }
    #penai-toggle{
      bottom:15px;
      right:15px;
      width:56px;
      height:56px;
      font-size:26px;
    }
  }
  
  /* Smaller phones */
  @media (max-width: 480px) {
    #emily-greeting-bubble{
      bottom:80px;
      font-size:13px;
      padding:15px 20px 15px 15px;
    }
    #emily-greeting-bubble p{
      font-size:13px;
      padding-right:18px;
    }
  }
  `;
  const style = document.createElement("style");
  style.id = "penai-styles";
  style.textContent = css;
  document.head.appendChild(style);
})();

// === Helper function to send resize messages to parent window ===
function sendResizeMessage(width, height) {
  try {
    if (window.parent && window.parent !== window) {
      console.log(`📏 Sending resize message: ${width}x${height}`);
      window.parent.postMessage({
        type: 'penai:resize',
        w: parseInt(width),
        h: parseInt(height)
      }, '*');
    }
  } catch (e) {
    console.log('Could not send resize message:', e);
  }
}

// === 3) Inject required DOM if missing ===
function ensureEl(tag, attrs = {}, parent = document.body) {
  const el = document.createElement(tag);
  Object.entries(attrs).forEach(([k, v]) => {
    if (k === "text") el.textContent = v;
    else if (k === "html") el.innerHTML = v;
    else el.setAttribute(k, v);
  });
  parent.appendChild(el);
  return el;
}

function ensureChatSkeleton() {
  // Toggle button
  if (!document.getElementById("penai-toggle")) {
    ensureEl("div", { id: "penai-toggle", "aria-label": "Open chat", text: "💬" });
  }

  // Chatbox container + header + body
  if (!document.getElementById("penai-chatbox")) {
    const box = ensureEl("div", { id: "penai-chatbox", "aria-live": "polite" });

    const header = ensureEl("div", { id: "penai-header" }, box);
    ensureEl("h2", { html: "Chat with Emily" }, header);

    // Language selector
    const lang = ensureEl("select", { id: "language-selector", "aria-label": "Language" }, header);
    lang.innerHTML = `
      <option value="en">🇬🇧 English</option>
      <option value="fr">🇫🇷 Français</option>
      <option value="es">🇪🇸 Español</option>
      <option value="de">🇩🇪 Deutsch</option>
      <option value="zh">🇨🇳 中文</option>
      <option value="ar">🇸🇦 العربية</option>
      <option value="it">🇮🇹 Italiano</option>
      <option value="ru">🇷🇺 Русский</option>
    `;

    // Controls
    ensureEl("button", { id: "start-button", class: "penai-ctl", text: "Start conversation" }, header);
    ensureEl("button", { id: "pause-button", class: "penai-ctl hidden", type: "button", text: "Pause" }, header);
    ensureEl("button", { id: "end-button", class: "penai-ctl hidden", type: "button", text: "End chat" }, header);
    ensureEl("button", { id: "penai-close", type: "button", "aria-label": "Close chat", html: "✕" }, header);

    // Body
    ensureEl("div", { id: "welcome-message" }, box);
    ensureEl("div", { id: "chat-history" }, box);
    ensureEl("div", { id: "thinking-text", text: "Thinking" }, box);
    ensureEl("div", { id: "button-grid" }, box);

    // Input row
    const inputRow = ensureEl("div", { id: "penai-input-container" }, box);
    ensureEl("input", { id: "question-input", type: "text", placeholder: "Ask a question…" }, inputRow);
    ensureEl("button", { id: "send-button", text: "Send" }, inputRow);
  }

  // Voice consent modal + indicator + audio
  if (!document.getElementById("voiceConsent")) {
    const modal = ensureEl("div", { id: "voiceConsent", style: "position:fixed;inset:0;background:rgba(0,0,0,.55);display:none;align-items:center;justify-content:center;z-index:999999;" });
    const panel = ensureEl("div", { style: "background:#fff;padding:20px;border-radius:12px;max-width:460px;width:92%;box-shadow:0 8px 30px rgba(0,0,0,.2);" }, modal);
    const row = ensureEl("div", { style: "display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:10px;" }, panel);
    ensureEl("h3", { id: "vc-title", style: "margin:0", text: "Enable Emily (voice)" }, row);
    const vcSel = ensureEl("select", { id: "vc-lang", style: "font-size:12px;padding:3px 6px;border-radius:4px;border:1px solid #ccc;background:#fff;color:#000;" }, row);
    vcSel.innerHTML = `
      <option value="en">🇬🇧 English</option>
      <option value="fr">🇫🇷 Français</option>
      <option value="es">🇪🇸 Español</option>
      <option value="de">🇩🇪 Deutsch</option>
      <option value="zh">🇨🇳 中文</option>
      <option value="ar">🇸🇦 العربية</option>
      <option value="it">🇮🇹 Italiano</option>
      <option value="ru">🇷🇺 Русский</option>
    `;
    ensureEl("p", { id: "vc-desc", text: "To chat by voice, we need one-time permission to use your microphone and play audio responses." }, panel);
    const lab = ensureEl("label", { style: "display:block;margin:8px 0;" }, panel);
    ensureEl("input", { id: "agreeVoice", type: "checkbox" }, lab);
    ensureEl("span", { id: "vc-agree", html: " I agree to voice processing for this session." }, lab);
    const btns = ensureEl("div", { style: "display:flex;gap:8px;justify-content:flex-end;margin-top:12px;" }, panel);
    ensureEl("button", { id: "cancelVoice", type: "button", text: "Not now" }, btns);
    ensureEl("button", { id: "startVoice", type: "button", text: "Start conversation", disabled: "" }, btns);
  }

  if (!document.getElementById("voiceIndicator")) {
    ensureEl("div", { id: "voiceIndicator", class: "voice-indicator hidden", style: "position:fixed;right:20px;bottom:700px;background:#fff;border:1px solid #ddd;border-radius:8px;padding:6px 10px;font-size:12px;box-shadow:0 4px 12px rgba(0,0,0,.1);", text: "Ready" });
  }
  if (!document.getElementById("aiAudio")) {
    ensureEl("audio", { id: "aiAudio", autoplay: "", playsinline: "" });
  }
  
  // Emily greeting bubble
  if (!document.getElementById("emily-greeting-bubble")) {
    const bubble = ensureEl("div", { id: "emily-greeting-bubble" });
    ensureEl("button", { class: "close-bubble", "aria-label": "Close", html: "✕" }, bubble);
    ensureEl("p", { id: "emily-greeting-text", text: "👋 Hi! I'm Emily, your voice-enabled admissions assistant. Click here to start a conversation!" }, bubble);
  }
}

// === IMPROVED: Emily Greeting System ===
function initEmilyGreeting() {
  const bubble = document.getElementById("emily-greeting-bubble");
  const greetingText = document.getElementById("emily-greeting-text");
  const closeBtn = bubble?.querySelector(".close-bubble");
  const toggleBtn = document.getElementById("penai-toggle");
  
  if (!bubble || !greetingText || !closeBtn || !toggleBtn) {
    console.log('⚠️ Emily greeting elements not found');
    return;
  }
  
  console.log('✅ Emily greeting system initialized');
  
  let greetingShown = false;
  let greetingTimeout = null;
  let greetingDismissed = false;
  
  // Check if user already dismissed greeting in this session
  try {
    if (sessionStorage.getItem('emily_greeting_dismissed') === 'true') {
      greetingDismissed = true;
      console.log('ℹ️ Greeting previously dismissed this session');
    }
  } catch (e) {
    console.log('Could not check session storage');
  }
  
  // Fetch personalized greeting from Emily
  function fetchGreeting() {
    // Start with generic message
    greetingText.innerHTML = "👋 Hi! I'm <strong>Emily</strong>, your voice-enabled admissions assistant. Click here to start a conversation!";
    
    if (!FAMILY_ID) {
      // No personalization available, just keep generic message
      return;
    }
    
    // Fetch personalized greeting
    fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ 
        question: "__GREETING__",
        language: "en",
        family_id: FAMILY_ID
      })
    })
    .then(r => r.json())
    .then(data => {
      if (data.answer) {
        // Wait 7 seconds, then change to personalized message
        setTimeout(() => {
          greetingText.textContent = data.answer;
          console.log('🔄 Switched to personalized greeting');
          
          // Reset auto-dismiss timer for 10 more seconds
          if (greetingTimeout) {
            clearTimeout(greetingTimeout);
          }
          greetingTimeout = setTimeout(() => {
            console.log('⏰ Auto-dismissing after personalized message');
            hideGreeting();
          }, 10000);
        }, 7000);
      }
    })
    .catch(() => {
      // If fetch fails, just keep generic message
      console.log('Could not fetch personalized greeting');
    });
  }
  
  // Show greeting bubble
  function showGreeting() {
    if (greetingShown || greetingDismissed) return;
    
    console.log('🎈 Showing Emily greeting bubble');
    greetingShown = true;
    
    fetchGreeting(); // This shows generic first, then switches to personalized
    
    // Delay before showing - longer on mobile/tablet for better UX
    const isMobile = window.innerWidth <= 768;
    const showDelay = isMobile ? 1500 : 800;
    
    setTimeout(() => {
      bubble.classList.add("show");
      
      // Initial auto-dismiss will be replaced if personalized message loads
      // This is just a fallback in case no personalization
      greetingTimeout = setTimeout(() => {
        console.log('⏰ Auto-dismissing greeting bubble (fallback)');
        hideGreeting();
      }, 18000); // 18 seconds fallback
    }, showDelay);
  }
  
  // Hide greeting bubble
  function hideGreeting() {
    console.log('👋 Hiding Emily greeting bubble');
    bubble.classList.remove("show");
    greetingDismissed = true;
    
    try {
      sessionStorage.setItem('emily_greeting_dismissed', 'true');
    } catch (e) {
      console.log('Could not save to session storage');
    }
    
    if (greetingTimeout) {
      clearTimeout(greetingTimeout);
      greetingTimeout = null;
    }
  }
  
  // Close button handler (touch + click)
  closeBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    e.preventDefault();
    hideGreeting();
  });
  
  // Touch support for close button
  closeBtn.addEventListener("touchend", (e) => {
    e.stopPropagation();
    e.preventDefault();
    hideGreeting();
  });
  
  // Click bubble to open chat (touch + click)
  bubble.addEventListener("click", (e) => {
    if (e.target === closeBtn || e.target.closest(".close-bubble")) return;
    console.log('💬 Bubble clicked - opening chat');
    hideGreeting();
    toggleBtn.click();
  });
  
  // Touch support for bubble
  bubble.addEventListener("touchend", (e) => {
    if (e.target === closeBtn || e.target.closest(".close-bubble")) return;
    console.log('💬 Bubble touched - opening chat');
    e.preventDefault();
    hideGreeting();
    toggleBtn.click();
  });
  
  // === Trigger logic: Multiple methods ===
  let triggered = false;
  
  function triggerGreeting() {
    if (triggered || greetingDismissed) return;
    triggered = true;
    console.log('✨ Greeting trigger activated');
    
    // Longer delay for smoother page experience, especially on mobile
    const isMobile = window.innerWidth <= 768;
    const triggerDelay = isMobile ? 1200 : 800;
    
    setTimeout(() => {
      showGreeting();
    }, triggerDelay);
  }
  
  // Method 1: Video detection (multiple strategies)
  const videoSelectors = [
    '#hero-video',
    '.hero-video',
    'video[autoplay]',
    '.video-hero video',
    'header video',
    '[data-hero-video]',
    'section video',
    '.banner video'
  ];
  
  function findAndWatchVideo() {
    let heroVideo = null;
    for (const selector of videoSelectors) {
      heroVideo = document.querySelector(selector);
      if (heroVideo) {
        console.log('🎥 Found hero video:', selector);
        
        // Strategy 1: Video actually ends
        heroVideo.addEventListener('ended', () => {
          console.log('🎬 Hero video ended - triggering greeting');
          triggerGreeting();
        });
        
        // Strategy 2: After 5 seconds of playing (whether muted or not)
        let playTime = 0;
        heroVideo.addEventListener('timeupdate', () => {
          if (heroVideo.currentTime >= 5 && playTime === 0) {
            playTime = heroVideo.currentTime;
            console.log('🎬 Video played 5+ seconds - triggering greeting');
            triggerGreeting();
          }
        });
        
        // Strategy 3: User interaction with video (play/pause)
        heroVideo.addEventListener('play', () => {
          setTimeout(() => {
            if (!triggered) {
              console.log('🎬 Video interaction detected - triggering greeting');
              triggerGreeting();
            }
          }, 5000); // Increased from 3s to 5s
        });
        
        // Strategy 4: If video exists but is muted/autoplay, trigger after longer delay
        // On mobile, autoplay often doesn't work, so this is key
        if (heroVideo.autoplay || heroVideo.muted) {
          setTimeout(() => {
            if (!triggered) {
              console.log('🎬 Autoplay/muted video timeout - triggering greeting');
              triggerGreeting();
            }
          }, 8000); // Increased from 6s to 8s
        }
        
        // Strategy 5: Mobile-specific - if video paused (iOS blocks autoplay), trigger with delay
        setTimeout(() => {
          if (heroVideo.paused && !triggered) {
            console.log('🎬 Video paused (mobile autoplay blocked) - triggering greeting');
            triggerGreeting();
          }
        }, 6000); // Increased from 4s to 6s
        
        return true;
      }
    }
    return false;
  }
  
  // Try to find video immediately
  const videoFound = findAndWatchVideo();
  
  // If no video found, try again after a short delay (for dynamic content)
  if (!videoFound) {
    setTimeout(() => {
      findAndWatchVideo();
    }, 1000);
  }
  
  // Method 2: Scroll detection (300px threshold)
  let lastScrollY = window.scrollY;
  const scrollThreshold = 300;
  let scrollCheckActive = true;
  
  function checkScroll() {
    if (!scrollCheckActive) return;
    
    const currentScrollY = window.scrollY;
    
    // User scrolled past threshold (going down)
    if (currentScrollY > scrollThreshold && lastScrollY <= scrollThreshold) {
      console.log('📜 Scrolled past threshold - triggering greeting');
      triggerGreeting();
      scrollCheckActive = false; // Stop checking after trigger
    }
    
    lastScrollY = currentScrollY;
  }
  
  window.addEventListener('scroll', checkScroll, { passive: true });
  
  // Method 3: Hero section observer
  const heroSelectors = [
    'header',
    '.hero',
    '.hero-section',
    '[data-hero]',
    '#hero',
    '.banner',
    'section:first-of-type'
  ];
  
  function findAndObserveHero() {
    let heroSection = null;
    for (const selector of heroSelectors) {
      heroSection = document.querySelector(selector);
      if (heroSection) {
        console.log('🏛️ Found hero section:', selector);
        
        const observer = new IntersectionObserver((entries) => {
          entries.forEach(entry => {
            // Hero section is leaving viewport (scrolled past)
            if (!entry.isIntersecting && entry.boundingClientRect.top < 0) {
              console.log('📜 Scrolled past hero section - triggering greeting');
              triggerGreeting();
              observer.disconnect(); // Stop observing after trigger
            }
          });
        }, { threshold: 0, rootMargin: '0px' });
        
        observer.observe(heroSection);
        return true;
      }
    }
    return false;
  }
  
  // Try to find and observe hero section
  setTimeout(() => {
    findAndObserveHero();
  }, 500);
  
  // Method 4: Time-based fallback (show after 8-10 seconds if no other trigger)
  const isMobile = window.innerWidth <= 768;
  const fallbackDelay = isMobile ? 10000 : 8000; // Longer on mobile
  
  const fallbackTimer = setTimeout(() => {
    if (!triggered && !greetingDismissed) {
      console.log('⏰ Fallback timer - triggering greeting');
      triggerGreeting();
    }
  }, fallbackDelay);
  
  // Clean up fallback timer if greeting triggered by other means
  const originalTrigger = triggerGreeting;
  triggerGreeting = function() {
    clearTimeout(fallbackTimer);
    originalTrigger();
  };
}

// === 4) Main app ===
document.addEventListener("DOMContentLoaded", () => {
  // Ensure skeleton exists
  ensureChatSkeleton();

  // Cache DOM refs
  const chatbox          = document.getElementById("penai-chatbox");
  const toggleBtn        = document.getElementById("penai-toggle");
  const closeBtn         = document.getElementById("penai-close");
  const history          = document.getElementById("chat-history");
  const input            = document.getElementById("question-input");
  const sendBtn          = document.getElementById("send-button");
  const thinking         = document.getElementById("thinking-text");
  const buttonGrid       = document.getElementById("button-grid");
  const languageSelector = document.getElementById("language-selector");
  const welcomeEl        = document.getElementById("welcome-message");

  // Safety check
  if (!chatbox || !toggleBtn || !closeBtn || !history || !input || !sendBtn || !thinking || !buttonGrid || !languageSelector || !welcomeEl) {
    console.error("🚫 Chatbot elements still missing – aborting.");
    return;
  }

  let currentLanguage = languageSelector.value;

  const UI_TEXT = {
    en: { welcome: "Hi there! Ask me anything about Cheltenham College.", placeholder: "Type your question…", enquire: "Enquire now" },
    fr: { welcome: "Bonjour ! Posez-moi vos questions sur Cheltenham College.", placeholder: "Tapez votre question…", enquire: "Faire une demande" },
    es: { welcome: "¡Hola! Pregúntame lo que quieras sobre Cheltenham College.", placeholder: "Escribe tu pregunta…", enquire: "Consultar ahora" },
    de: { welcome: "Hallo! Fragen Sie mich alles über Cheltenham College.", placeholder: "Geben Sie Ihre Frage ein…", enquire: "Jetzt anfragen" },
    zh: { welcome: "您好！欢迎咨询 Cheltenham College。", placeholder: "请输入问题…", enquire: "现在咨询" },
    it: { welcome: "Ciao! Chiedimi qualsiasi cosa su Cheltenham College.", placeholder: "Scrivi la tua domanda…", enquire: "Richiedi informazioni" },
    ar: { welcome: "مرحبًا! اسألني أي شيء عن Cheltenham College.", placeholder: "اكتب سؤالك…", enquire: "أرسل استفسارًا" },
    ru: { welcome: "Здравствуйте! Задайте мне любой вопрос о Cheltenham College.", placeholder: "Введите ваш вопрос…", enquire: "Оставить заявку" }
  };
  
  const LABELS = {
    en: { fees: "Fees", admissions: "Admissions", contact: "Contact", open: "Open Events", enquire: UI_TEXT.en.enquire, prospectus: "Tailored Prospectus" },
    fr: { fees: "Frais", admissions: "Admissions", contact: "Contact", open: "Portes ouvertes", enquire: UI_TEXT.fr.enquire, prospectus: "Prospectus personnalisé" },
    es: { fees: "Tasas", admissions: "Admisiones", contact: "Contacto", open: "Jornadas abiertas", enquire: UI_TEXT.es.enquire, prospectus: "Prospecto personalizado" },
    de: { fees: "Gebühren", admissions: "Aufnahme", contact: "Kontakt", open: "Tage der offenen Tür", enquire: UI_TEXT.de.enquire, prospectus: "Individuelles Prospekt" },
    zh: { fees: "学费", admissions: "招生", contact: "联系方式", open: "开放日", enquire: UI_TEXT.zh.enquire, prospectus: "定制版招生简章" },
    it: { fees: "Rette", admissions: "Ammissioni", contact: "Contatti", open: "Open Day", enquire: UI_TEXT.it.enquire, prospectus: "Prospetto personalizzato" },
    ar: { fees: "الرسوم", admissions: "القبول", contact: "التواصل", open: "الأيام المفتوحة", enquire: UI_TEXT.ar.enquire, prospectus: "كتيّب مخصص" },
    ru: { fees: "Стоимость обучения", admissions: "Поступление", contact: "Контакты", open: "Дни открытых дверей", enquire: UI_TEXT.ru.enquire, prospectus: "Индивидуальный проспект" }
  };

  function clearButtons(){ buttonGrid.innerHTML = ""; }
  function getTranslatedLabel(k){ return LABELS[currentLanguage]?.[k] || k; }

  function createButton(label, query) {
    const btn = document.createElement("button");
    btn.className = "quick-reply";
    btn.innerText = label;
    btn.onclick = () => sendMessage(query);
    buttonGrid.appendChild(btn);
  }

  function showInitialButtons() {
    clearButtons();
    ["fees", "admissions", "contact", "open", "enquire", "prospectus"].forEach(key => {
      createButton(getTranslatedLabel(key), key);
    });
  }

  function appendExchange(questionText, answerText, url = null, linkLabel = null) {
    const exchangeDiv = document.createElement("div");
    exchangeDiv.className = "exchange";

    const userDiv = document.createElement("div");
    userDiv.className = "message user";
    const userP = document.createElement("p");

    const userPrefix = { en:"Me:", fr:"Moi :", de:"Ich:", es:"Yo:", zh:"我：" }[currentLanguage] || "Me:";
    const cleanedQ = questionText.replace(/^Me:|^Moi\s*:|^Ich:|^Yo:|^我：/, '').trim();
    userP.textContent = `${userPrefix} ${cleanedQ}`;
    userDiv.appendChild(userP);

    const botDiv = document.createElement("div");
    botDiv.className = "message bot";
    const botP = document.createElement("p");
    botP.textContent = answerText;
    botDiv.appendChild(botP);

    if (url && linkLabel) {
      const a = document.createElement("a");
      a.href = url; a.target = "_blank"; a.className = "chat-link"; a.textContent = linkLabel;
      botDiv.appendChild(a);
    }

    exchangeDiv.appendChild(userDiv);
    exchangeDiv.appendChild(botDiv);
    history.appendChild(exchangeDiv);
    history.scrollTop = history.scrollHeight;
  }

  function updateWelcome() {
    const t = UI_TEXT[currentLanguage] || UI_TEXT.en;
    
    // If we have a family_id, fetch personalized welcome
    if (FAMILY_ID) {
      fetch("/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          question: "__WELCOME__",
          language: currentLanguage,
          family_id: FAMILY_ID
        })
      })
      .then(r => r.json())
      .then(data => {
        welcomeEl.innerText = data.answer || t.welcome;
      })
      .catch(() => {
        welcomeEl.innerText = t.welcome;
      });
    } else {
      welcomeEl.innerText = t.welcome;
    }
    
    input.placeholder = t.placeholder;
  }

  function renderDynamicButtons(queries = [], queryMap = {}) {
    clearButtons();
    // Always add Enquire first
    const t = UI_TEXT[currentLanguage] || UI_TEXT.en;
    createButton(t.enquire, "enquiry");

    // Add up to 5 contextual
    let count = 0;
    for (const key of queries) {
      if ((key || "").toLowerCase() === "enquiry") continue;
      const label = queryMap[key] || getTranslatedLabel(key);
      createButton(label, key);
      if (++count === 5) break;
    }

    // Pad with defaults if fewer than 5
    if (count < 5) {
      const defaults = ["fees", "admissions", "open", "contact", "prospectus"];
      for (const key of defaults) {
        if (queries.includes(key) || key === "enquiry") continue;
        createButton(getTranslatedLabel(key), key);
        if (++count === 5) break;
      }
    }
  }

  function sendMessage(msgText) {
    const rawQ = (msgText || input.value).trim();
    if (!rawQ) return;

    const cleanedQ = rawQ.replace(/^Me:|^Moi\s*:|^Ich:|^Yo:|^我：/, '').trim();

    input.value = "";
    
    // Show user message immediately
    const userPrefix = { en:"Me:", fr:"Moi :", de:"Ich:", es:"Yo:", zh:"我：" }[currentLanguage] || "Me:";
    const userDiv = document.createElement("div");
    userDiv.className = "message user";
    const userP = document.createElement("p");
    userP.textContent = `${userPrefix} ${cleanedQ}`;
    userDiv.appendChild(userP);
    history.appendChild(userDiv);
    history.scrollTop = history.scrollHeight;
    
    // Hide welcome and buttons
    welcomeEl.style.display = "none";
    clearButtons();
    
    // Show thinking indicator after a brief pause (so user sees their message first)
    setTimeout(() => {
      thinking.style.display = "block";
    }, 500);

    const startTime = Date.now();

    fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ 
        question: cleanedQ, 
        language: currentLanguage,
        family_id: FAMILY_ID
      })
    })
    .then(r => r.json())
    .then(data => {
      // Calculate how long the request took
      const elapsed = Date.now() - startTime;
      // Ensure minimum 7 seconds between user message and Emily's response
      const minDelay = 7000;
      const remainingDelay = Math.max(0, minDelay - elapsed);
      
      setTimeout(() => {
        thinking.style.display = "none";
        
        // Show Emily's response
        const botDiv = document.createElement("div");
        botDiv.className = "message bot";
        const botP = document.createElement("p");
        botP.textContent = data.answer;
        botDiv.appendChild(botP);

        if (data.url && data.link_label) {
          const a = document.createElement("a");
          a.href = data.url; 
          a.target = "_blank"; 
          a.className = "chat-link"; 
          a.textContent = data.link_label;
          botDiv.appendChild(a);
        }

        history.appendChild(botDiv);
        history.scrollTop = history.scrollHeight;
        
        // Wait 10 seconds before showing buttons (so user can read Emily's response)
        setTimeout(() => {
          if (data.queries && data.queries.length) renderDynamicButtons(data.queries, data.query_map);
          else showInitialButtons();
        }, 10000);
      }, remainingDelay);
    })
    .catch(err => {
      const elapsed = Date.now() - startTime;
      const minDelay = 7000;
      const remainingDelay = Math.max(0, minDelay - elapsed);
      
      setTimeout(() => {
        thinking.style.display = "none";
        console.error("❌ Fetch error:", err);
        
        const botDiv = document.createElement("div");
        botDiv.className = "message bot";
        const botP = document.createElement("p");
        botP.textContent = "Something went wrong – please try again.";
        botDiv.appendChild(botP);
        history.appendChild(botDiv);
        history.scrollTop = history.scrollHeight;
        
        // Wait 10 seconds before showing buttons
        setTimeout(() => {
          showInitialButtons();
        }, 10000);
      }, remainingDelay);
    });
  }

  // Toggle / close with resize messages
  toggleBtn.addEventListener("click", () => {
    chatbox.classList.toggle("open");
    if (chatbox.classList.contains("open")) {
      sendResizeMessage(400, 600);
      updateWelcome();
      showInitialButtons();
      input.focus();
    } else {
      sendResizeMessage(64, 64);
    }
  });
  
  closeBtn.addEventListener("click", () => {
    chatbox.classList.remove("open");
    sendResizeMessage(64, 64);
  });

  // Send initial resize message on load
  setTimeout(() => {
    sendResizeMessage(64, 64);
  }, 1000);

  // Language + send
  languageSelector.addEventListener("change", () => { 
    currentLanguage = languageSelector.value; 
    updateWelcome(); 
    showInitialButtons(); 
  });
  sendBtn.addEventListener("click", () => sendMessage());
  input.addEventListener("keypress", e => { if (e.key === "Enter") sendMessage(); });

  // Init UI
  updateWelcome();
  showInitialButtons();

  // === Initialize Emily greeting system ===
  initEmilyGreeting();

  // === Load voice helper file ===
  const hasVoice = !!document.querySelector('script[src*="realtime-voice-handsfree.js"]');
  if (!hasVoice) {
    const s = document.createElement("script");
    s.src = CHATBOT_ORIGIN + "/static/realtime-voice-handsfree.js";
    s.async = true;
    document.body.appendChild(s);
  }
});