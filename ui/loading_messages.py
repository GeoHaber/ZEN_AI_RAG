# -*- coding: utf-8 -*-
"""
ui/loading_messages.py - Fun loading messages for chat interface
"""

import random


# Waiting for user input messages
WAITING_FOR_USER = [
    "💭 Waiting for your brilliant ideas...",
    "✨ Ready when you are...",
    "🎯 Standing by for your next question...",
    "🌟 Your wish is my command...",
    "💡 Awaiting your input...",
    "🚀 Ready to help whenever you're ready...",
    "🎨 Canvas ready for your thoughts...",
    "⚡ Charged up and waiting...",
    "🧠 Brain warmed up, waiting for you...",
    "📝 Pen poised, what's on your mind?",
    "🎪 The stage is yours...",
    "🎬 Action! (whenever you're ready)",
    "🎵 Humming quietly, awaiting your tune...",
    "☕ Sipping virtual coffee, waiting patiently...",
    "🌈 Rainbow loaded, just need your question...",
]

# LLM thinking/processing messages
LLM_THINKING = [
    "🤔 Thinking deeply...",
    "🧠 Neurons firing...",
    "⚙️ Crunching the numbers...",
    "🔮 Consulting the oracle...",
    "🎲 Rolling the dice of wisdom...",
    "🌊 Diving into the knowledge sea...",
    "🔍 Searching through the archives...",
    "✨ Summoning the answer spirits...",
    "🎯 Calculating the perfect response...",
    "🚂 Training of thought departing...",
    "🧮 Doing the math...",
    "📚 Flipping through digital pages...",
    "🎨 Painting your answer...",
    "🔬 Running the experiments...",
    "🌟 Aligning the stars of logic...",
    "⚡ Charging up the response...",
    "🎪 Juggling ideas...",
    "🏗️ Building your response brick by brick...",
    "🎵 Composing the perfect reply...",
    "🍳 Cooking up something good...",
    "🔭 Scanning the knowledge universe...",
    "🎰 Hit the jackpot of wisdom! Almost there...",
    "🧩 Assembling the answer puzzle...",
    "🎬 Directing the response scene...",
    "🌊 Surfing the data waves...",
]

# RAG-specific thinking messages
RAG_THINKING = [
    "📖 Reading through your documents...",
    "🔎 Searching the knowledge base...",
    "📚 Cross-referencing sources...",
    "🗂️ Indexing through information...",
    "🎯 Finding the perfect match...",
    "🌐 Scanning the web archive...",
    "🔗 Connecting the dots...",
    "📊 Analyzing the data...",
    "🗃️ Rummaging through the files...",
    "🎓 Consulting the library...",
    "🔍 Magnifying the details...",
    "📑 Reviewing the documentation...",
    "🏛️ Accessing the archives...",
    "🗺️ Mapping the knowledge terrain...",
    "🧬 Sequencing information strands...",
]

# Swarm mode thinking messages
SWARM_THINKING = [
    "🐝 Consulting the expert swarm...",
    "👥 Gathering collective wisdom...",
    "🎯 Polling the experts...",
    "🌊 Hive mind activating...",
    "🎪 Assembling the dream team...",
    "🎭 Experts taking the stage...",
    "🏛️ Council in session...",
    "🎓 Academic panel deliberating...",
    "🔮 Multiple oracles conferring...",
    "🎨 Artists' collective at work...",
    "🧠 Brains trust activated...",
    "⚡ Swarm intelligence powering up...",
    "🌟 Stars aligning (literally, multiple models)...",
    "🎯 Precision team assembled...",
    "🚀 Squadron ready for launch...",
]


def get_waiting_message() -> str:
    """Get a random waiting-for-user message."""
    return random.choice(WAITING_FOR_USER)


def get_thinking_message(use_rag: bool = False, use_swarm: bool = False) -> str:
    """
    Get a random thinking message based on context.

    Args:
        use_rag: Whether RAG is being used
        use_swarm: Whether swarm mode is active

    Returns:
        Random appropriate message
    """
    if use_swarm:
        return random.choice(SWARM_THINKING)
    elif use_rag:
        return random.choice(RAG_THINKING)
    else:
        return random.choice(LLM_THINKING)


def get_spinner_icon() -> str:
    """Get a random spinner icon."""
    spinners = ["⏳", "⌛", "🔄", "⚡", "✨", "🌟", "💫", "🎯"]
    return random.choice(spinners)
