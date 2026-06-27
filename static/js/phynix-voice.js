// phynix-voice.js — Mic button + Web Speech API + Whisper fallback

(function () {
  "use strict";

  let mediaRecorder = null;
  let audioChunks = [];
  let isRecording = false;
  let recognition = null;

  // ── Web Speech API (instant, no server) ──────────────────────────
  function initSpeechRecognition() {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return null;

    const r = new SpeechRecognition();
    r.continuous = false;
    r.interimResults = true;
    r.lang = "en-US";
    return r;
  }

  // ── Main setup ────────────────────────────────────────────────────
  function setupMicButton() {
    const micBtn = document.getElementById("mic-btn");
    const chatTextarea = document.getElementById("chat-input");
    const voicePreview = document.getElementById("voice-preview");

    if (!micBtn || !chatTextarea) return;

    recognition = initSpeechRecognition();

    // ── Case 1: Browser supports Web Speech API ──
    if (recognition) {
      recognition.onstart = () => {
        isRecording = true;
        micBtn.classList.add("recording");
        micBtn.setAttribute("aria-label", "Stop recording");
        if (voicePreview) {
          voicePreview.textContent = "Listening...";
        }
      };

      recognition.onresult = (event) => {
        let interim = "";
        let final = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const t = event.results[i][0].transcript;
          if (event.results[i].isFinal) final += t;
          else interim += t;
        }
        if (voicePreview) {
          voicePreview.textContent = final || interim || "Listening...";
        }
        if (final) {
          chatTextarea.value =
            (chatTextarea.value ? chatTextarea.value + " " : "") + final;
          autoResize(chatTextarea);
        }
      };

      recognition.onerror = (e) => {
        console.warn("Speech recognition error:", e.error);
        stopRecording();
        if (voicePreview) voicePreview.textContent = "";
      };

      recognition.onend = () => {
        stopRecording();
        if (voicePreview) {
          setTimeout(() => {
            voicePreview.textContent = "";
          }, 1500);
        }
      };

      micBtn.addEventListener("click", () => {
        if (isRecording) {
          recognition.stop();
        } else {
          recognition.start();
        }
      });

      return; // done for Speech API path
    }

    // ── Case 2: Fallback — record audio, send to Whisper endpoint ──
    micBtn.addEventListener("click", async () => {
      if (isRecording) {
        stopMediaRecorder();
        return;
      }

      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: true,
        });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = (e) => {
          if (e.data.size > 0) audioChunks.push(e.data);
        };

        mediaRecorder.onstop = async () => {
          const blob = new Blob(audioChunks, { type: "audio/webm" });
          stream.getTracks().forEach((t) => t.stop());

          if (voicePreview) voicePreview.textContent = "Transcribing...";

          const formData = new FormData();
          formData.append("audio", blob, "voice.webm");

          try {
            const resp = await fetch("/voice/transcribe/", {
              method: "POST",
              headers: {
                "X-CSRFToken": getCsrf(),
              },
              body: formData,
            });
            const data = await resp.json();
            if (data.text) {
              chatTextarea.value =
                (chatTextarea.value ? chatTextarea.value + " " : "") +
                data.text;
              autoResize(chatTextarea);
              if (voicePreview) {
                voicePreview.textContent = data.text;
                setTimeout(() => (voicePreview.textContent = ""), 2000);
              }
            }
          } catch (err) {
            console.error("Whisper transcription failed:", err);
            if (voicePreview) voicePreview.textContent = "";
          }

          stopRecording();
        };

        mediaRecorder.start();
        isRecording = true;
        micBtn.classList.add("recording");
        if (voicePreview) voicePreview.textContent = "Recording...";
      } catch (err) {
        console.error("Microphone access denied:", err);
        if (voicePreview)
          voicePreview.textContent = "Mic access denied. Check permissions.";
      }
    });
  }

  function stopMediaRecorder() {
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
    }
  }

  function stopRecording() {
    isRecording = false;
    const micBtn = document.getElementById("mic-btn");
    if (micBtn) {
      micBtn.classList.remove("recording");
      micBtn.setAttribute("aria-label", "Start voice input");
    }
  }

  // ── Textarea auto-resize ──────────────────────────────────────────
  function autoResize(el) {
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
  }

  // ── CSRF helper ──────────────────────────────────────────────────
  function getCsrf() {
    const cookie = document.cookie
      .split(";")
      .map((c) => c.trim())
      .find((c) => c.startsWith("csrftoken="));
    return cookie ? cookie.split("=")[1] : "";
  }

  // ── Chip prompts (click to fill textarea) ────────────────────────
  function setupChips() {
    document.querySelectorAll(".prompt-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        const textarea = document.getElementById("chat-input");
        if (textarea) {
          textarea.value = chip.dataset.text || chip.textContent.trim();
          textarea.focus();
          autoResize(textarea);
        }
      });
    });
  }

  // ── Auto-resize on input ─────────────────────────────────────────
  function setupTextareaResize() {
    const textarea = document.getElementById("chat-input");
    if (!textarea) return;
    textarea.addEventListener("input", () => autoResize(textarea));
  }

  // ── Send on Enter (Shift+Enter for newline) ───────────────────────
  function setupEnterToSend() {
    const textarea = document.getElementById("chat-input");
    const form = document.getElementById("chat-form");
    if (!textarea || !form) return;

    textarea.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        form.dispatchEvent(new Event("submit", { bubbles: true }));
      }
    });
  }

  // ── Scroll to bottom after HTMX swap ────────────────────────────
  function scrollToBottom() {
    const msgs = document.getElementById("chat-messages");
    if (msgs) msgs.scrollTop = msgs.scrollHeight;
  }

  document.addEventListener("DOMContentLoaded", () => {
    setupMicButton();
    setupChips();
    setupTextareaResize();
    setupEnterToSend();
    scrollToBottom();
  });

  // Re-scroll after HTMX content swap
  document.addEventListener("htmx:afterSwap", (e) => {
    if (e.detail.target && e.detail.target.id === "chat-messages") {
      scrollToBottom();
      // Clear input after send
      const textarea = document.getElementById("chat-input");
      if (textarea) {
        textarea.value = "";
        autoResize(textarea);
      }
    }
  });
})();
