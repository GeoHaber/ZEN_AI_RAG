document.addEventListener('DOMContentLoaded', () => {
    // --- Configuration ---
    const config = {
        botName: "Zena",
        botIcon: "ri-customer-service-2-fill", // Using a reliable icon
        welcomeMessage: "👋 Bun venit!<br><br>Dacă aveți nevoie de o programare sau de informații despre spital, sunt aici.<br><br>Nu uitați că încă învăț, așa că este posibil ca ocazional să fac greșeli.<br><br>Cum vă pot ajuta astăzi?",
        quickQuestions: [
            "Cum pot face o programare?",
            "Ce servicii oferă spitalul?",
            "Documente necesare internare",
            "Unde vă găsesc?"
        ],
        mockResponses: {
            "programare": "Pentru programări, ne puteți contacta telefonic la 0259.123.456 între orele 08:00 - 16:00, sau puteți folosi formularul online de pe site-ul nostru.",
            "servicii": "Spitalul oferă o gamă largă de servicii: Cardiologie, Neurologie, Pediatrie, Chirurgie Generală și UPU. Doriți detalii despre o secție anume?",
            "documente": "Pentru internare aveți nevoie de: Bilet de trimitere, Card de sănătate, Carte de identitate și Adeverință de salariat/talon de pensie.",
            "locatie": "Ne găsiți pe Str. Gheorghe Doja nr. 65, Oradea, Bihor.",
            "default": "Îmi pare rău, încă învăț și nu am înțeles exact. Puteți reformula sau alege una dintre opțiunile de mai jos?"
        }
    };

    // --- Elements ---
    const widget = document.getElementById('zena-widget');
    const toggleBtn = document.getElementById('zena-toggle-btn');
    const closeBtn = document.getElementById('zena-close-btn');
    const windowEl = document.getElementById('zena-window');
    const messagesContainer = document.getElementById('zena-messages');
    const input = document.getElementById('zena-input');
    const sendBtn = document.getElementById('zena-send-btn');
    const quickActionsContainer = document.getElementById('zena-quick-actions');

    let isOpen = false;

    // --- Functions ---

    function toggleChat() {
        isOpen = !isOpen;
        if (isOpen) {
            windowEl.classList.remove('hidden');
            toggleBtn.classList.add('hidden'); // Optional: hide button when open
            // Focus input after transition
            setTimeout(() => input.focus(), 300);

            // Initial render if empty
            if (messagesContainer.children.length === 0) {
                renderMessage(config.welcomeMessage, 'bot');
                renderQuickActions();
            }
        } else {
            windowEl.classList.add('hidden');
            toggleBtn.classList.remove('hidden');
        }
    }

    function renderMessage(text, sender) {
        const row = document.createElement('div');
        row.className = `message-row ${sender}`;

        let avatarHtml = '';
        if (sender === 'bot') {
            avatarHtml = `
                <div class="message-avatar">
                   <i class="${config.botIcon}"></i>
                </div>
            `;
        }

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        bubble.innerHTML = text;

        if (sender === 'bot') {
            row.innerHTML = avatarHtml;
            row.appendChild(bubble);
        } else {
            row.appendChild(bubble); // User doesn't show avatar usually, or add if needed
        }

        messagesContainer.appendChild(row);
        scrollToBottom();
    }

    function renderTypingIndicator() {
        const row = document.createElement('div');
        row.id = 'typing-indicator-row';
        row.className = 'message-row bot';

        row.innerHTML = `
            <div class="message-avatar">
                <i class="${config.botIcon}"></i>
            </div>
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        `;

        messagesContainer.appendChild(row);
        scrollToBottom();
    }

    function removeTypingIndicator() {
        const el = document.getElementById('typing-indicator-row');
        if (el) el.remove();
    }

    function renderQuickActions() {
        quickActionsContainer.innerHTML = '';
        config.quickQuestions.forEach(q => {
            const btn = document.createElement('button');
            btn.className = 'quick-btn';
            btn.textContent = q;
            btn.onclick = () => handleUserMessage(q);
            quickActionsContainer.appendChild(btn);
        });
    }

    function scrollToBottom() {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    async function getBotResponse(text) {
        // Try to call RAG_RAT API
        try {
            const response = await fetch('http://localhost:8000/v1/chat/completions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    messages: [
                        { role: "system", content: "You are Zena, a helpful virtual assistant for Spitalul Județean Bihor. Answer briefly in Romanian." },
                        { role: "user", content: text }
                    ],
                    temperature: 0.7,
                    max_tokens: 150
                })
            });

            if (response.ok) {
                const data = await response.json();
                return data.choices[0].message.content;
            }
        } catch (error) {
            // [X-Ray auto-fix] console.warn("API unavailable, using mock data.", error);
        }

        // Fallback to mock data if API fails
        const lowerText = text.toLowerCase();

        if (lowerText.includes('programare') || lowerText.includes('programări')) return config.mockResponses.programare;
        if (lowerText.includes('servici') || lowerText.includes('sectii')) return config.mockResponses.servicii;
        if (lowerText.includes('document') || lowerText.includes('act')) return config.mockResponses.documente;
        if (lowerText.includes('unde') || lowerText.includes('adresa') || lowerText.includes('locatie')) return config.mockResponses.locatie;

        return config.mockResponses.default;
    }

    async function handleUserMessage(text) {
        if (!text.trim()) return;

        // 1. Render User Message
        renderMessage(text, 'user');
        input.value = '';

        // 2. Show Typing Indicator
        renderTypingIndicator();

        // 3. Get Response (Async)
        const responseText = await getBotResponse(text);

        // Random delay for realism (only if using mock, API has its own latency)
        // If API was fast, we still want a tiny delay for UX
        setTimeout(() => {
            removeTypingIndicator();
            renderMessage(responseText, 'bot');
        }, 500);
    }

    // --- Event Listeners ---

    toggleBtn.addEventListener('click', toggleChat);
    closeBtn.addEventListener('click', toggleChat);

    sendBtn.addEventListener('click', () => {
        handleUserMessage(input.value);
    });

    const micBtnInput = document.getElementById('zena-mic-input-btn');
    if (micBtnInput) {
        micBtnInput.addEventListener('click', () => {
            alert('Funcția de dictare necesită permisiuni de browser (API-ul Web Speech).');
        });
    }

    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleUserMessage(input.value);
        }
    });

    // Close on click outside (optional, good UX)
    /*
    document.addEventListener('click', (e) => {
        if (isOpen && !widget.contains(e.target)) {
            toggleChat();
        }
    });
    */
});
