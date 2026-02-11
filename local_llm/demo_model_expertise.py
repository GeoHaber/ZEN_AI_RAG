#!/usr/bin/env python3
"""
Demo: Enhanced Model Card with Expertise & Skill Qualification

Shows how the model card system displays the expertise and skill set
of each LLM "brain" in the system.
"""

from enhanced_model_card import EnhancedModelRegistry, ModelMetadata


def demo_individual_models():
    """Display individual model expertise"""
    print("\n" + "=" * 80)
    print("🧠 INDIVIDUAL MODEL EXPERTISE SHOWCASE")
    print("=" * 80)
    
    registry = EnhancedModelRegistry()
    
    # Define models to showcase
    models = [
        ("mistral-7b", "mistral-7b-Q4_K_M.gguf", 4.0),
        ("qwen2.5-14b", "qwen-14b-Q5_K_M.gguf", 8.2),
        ("gemma-2-9b", "gemma-9b-Q4_K_M.gguf", 4.8),
    ]
    
    for model_id, filename, size_gb in models:
        print()
        metadata = registry.enrich_model(model_id, filename, size_gb)
        print(metadata.human_summary())
        print()


def demo_expertise_comparison():
    """Compare expertise across models"""
    print("\n" + "=" * 80)
    print("⚖️  EXPERTISE COMPARISON")
    print("=" * 80)
    
    registry = EnhancedModelRegistry()
    
    # Get expertise for different models
    models_to_compare = [
        ("Mistral-7B", "mistral-7b", "Reasoning & Analysis"),
        ("Qwen-14B", "qwen2.5-14b", "Multilingual & Math"),
        ("Gemma-9B", "gemma-2-9b", "Conversation & Creativity"),
    ]
    
    for display_name, model_id, description in models_to_compare:
        expertise = registry._get_model_expertise(model_id)
        
        print(f"\n┌─ {display_name} ({description})")
        print(f"│")
        print(f"├─ Expert Areas:")
        for area in expertise['expertise_areas'][:3]:  # Top 3
            print(f"│  ★ {area}")
        
        print(f"│")
        print(f"├─ Professional Skills:")
        expert_skills = {k: v for k, v in expertise['skills'].items() if v == 'expert'}
        for skill, level in list(expert_skills.items())[:3]:
            print(f"│  ⭐ {skill.title()}: {level}")
        
        print(f"│")
        print(f"└─ Use For: {', '.join([s for s in expertise['skills'].keys()][:4]).title()}")


def demo_skill_proficiency():
    """Show how skill proficiency levels are displayed"""
    print("\n" + "=" * 80)
    print("📊 SKILL PROFICIENCY LEVELS")
    print("=" * 80)
    
    # Create a demo model with mixed proficiency levels
    demo_model = ModelMetadata(
        model_id="demo-model",
        model_name="Demonstration Model",
        base_model="demo",
        quantization="Q4_K",
        file_size_gb=7.0,
        context_window=8192,
        expertise_areas=[
            "Multi-domain reasoning",
            "Complex problem solving",
            "Advanced dialogue",
        ],
        skills={
            'reasoning': 'expert',
            'conversation': 'expert',
            'coding': 'advanced',
            'math': 'advanced',
            'instruction_following': 'intermediate',
            'creative_writing': 'intermediate',
        }
    )
    
    print(demo_model.human_summary())


def demo_use_case_selection():
    """Help select the right brain for a specific task"""
    print("\n" + "=" * 80)
    print("🎯 BRAIN SELECTION BY USE CASE")
    print("=" * 80)
    
    use_cases = {
        "Mathematical Reasoning": "qwen2.5-14b",
        "Code Generation": "mistral-7b",
        "Multilingual Support": "qwen2.5-14b",
        "Conversational AI": "gemma-2-9b",
        "Complex Analysis": "mistral-7b",
    }
    
    registry = EnhancedModelRegistry()
    
    print("\nRecommended Model Selections:\n")
    
    for use_case, model_id in use_cases.items():
        expertise = registry._get_model_expertise(model_id)
        
        # Find most relevant skills for this use case
        relevant_skills = {k: v for k, v in expertise['skills'].items() 
                         if all(word in k.lower() for word in use_case.lower().split())
                         or 'expert' in v}
        
        print(f"📌 {use_case}")
        print(f"   → Recommended: {model_id.replace('-7b', ' 7B').replace('-14b', ' 14B').replace('-9b', ' 9B').title()}")
        print(f"   → Strengths: {', '.join(expertise['expertise_areas'][:2])}")
        print()


def main():
    """Run all demonstrations"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  🧠 ENHANCED MODEL CARD - EXPERTISE & SKILL QUALIFICATION DEMO".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "═" * 78 + "╝")
    
    # Run all demos
    demo_individual_models()
    demo_expertise_comparison()
    demo_skill_proficiency()
    demo_use_case_selection()
    
    # Summary
    print("\n" + "=" * 80)
    print("✅ SUMMARY")
    print("=" * 80)
    print("""
The enhanced model card system now qualifies the expertise and skill set of each
LLM "brain". Key features:

🧠 EXPERTISE AREAS
   Each model is defined by its core areas of mastery
   (e.g., "Logical reasoning", "Multilingual understanding")

⭐ PROFICIENCY LEVELS
   Skills are rated: Expert, Advanced, Intermediate
   Visual indicators (⭐⭐⭐, ⭐⭐, ⭐) make complexity obvious

🎯 USE CASE MATCHING
   Model selection is now data-driven by expertise
   Non-technical users can understand what each brain excels at

📊 HUMAN-FRIENDLY OUTPUT
   Expertise information is displayed in plain language
   No technical jargon - clear professional assessment

The model cards now answer: "What are this brain's superpowers?"
""")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
