#!/usr/bin/env python3
"""
Quick check to see if including RL environments changes the RL paper count significantly.
"""

import json
import sys
from collections import defaultdict, Counter

sys.path.insert(0, '/home/bouthilx/projects/paperext/src')
from paperext.utils import Paper

def quick_environment_analysis():
    """Quick analysis of RL environment usage vs dataset usage."""
    
    # Load original dataset results
    with open('dataset_domain_comparison.json', 'r') as f:
        dataset_data = json.load(f)
    
    original_rl_count = dataset_data['dataset_domain_stats'].get('Reinforcement Learning & Robotics', 0)
    
    print(f"Original RL count (datasets only): {original_rl_count}")
    
    # Load papers data
    data_path = '/home/bouthilx/projects/paperext/data/paperoni-2019-01-01-2025-01-01-PR_2025-05-29.json'
    with open(data_path, 'r') as f:
        papers_data = json.load(f)
    
    # RL environment keywords - comprehensive list
    rl_env_keywords = [
        'atari', 'gym', 'openai gym', 'gymnasium', 'mujoco', 'dm control',
        'deepmind lab', 'starcraft', 'dota', 'minecraft', 'procgen',
        'halfcheetah', 'hopper', 'walker', 'ant', 'humanoid',
        'cartpole', 'cart-pole', 'mountain car', 'acrobot',
        'lunar lander', 'bipedal walker', 'car racing',
        'environment', 'simulator', 'simulation',
        'policy', 'reward', 'agent', 'episode', 'trajectory',
        'q-learning', 'policy gradient', 'actor-critic',
        'ppo', 'sac', 'ddpg', 'td3', 'dqn'
    ]
    
    rl_papers_with_envs = 0
    sample_rl_papers = []
    
    print("Scanning papers for RL environments...")
    
    processed = 0
    for i, paper_json in enumerate(papers_data):
        if i % 500 == 0:
            print(f"Processed {i}/{len(papers_data)} papers, found {rl_papers_with_envs} RL papers")
        
        try:
            paper = Paper(paper_json)
            if not paper.queries:
                continue
                
            processed += 1
            
            with open(paper.queries[0], 'r') as f:
                analysis_data = json.load(f)
            
            extractions = analysis_data.get('extractions', {})
            if not extractions:
                continue
            
            # Get all text from the paper analysis
            title = paper_json.get('title', '')
            description = extractions.get('description', {})
            if isinstance(description, dict):
                desc_text = description.get('value', '') + ' ' + description.get('justification', '')
            else:
                desc_text = str(description)
            
            # Check datasets field
            datasets = extractions.get('datasets', [])
            dataset_text = ''
            for dataset in datasets:
                if isinstance(dataset, dict) and 'name' in dataset:
                    name_data = dataset['name']
                    if isinstance(name_data, dict):
                        dataset_text += name_data.get('value', '') + ' '
                        dataset_text += name_data.get('justification', '') + ' '
            
            # Combine all text
            full_text = (title + ' ' + desc_text + ' ' + dataset_text).lower()
            
            # Check for RL environment keywords
            rl_matches = []
            for keyword in rl_env_keywords:
                if keyword in full_text:
                    rl_matches.append(keyword)
            
            if len(rl_matches) >= 2:  # Require at least 2 RL keywords
                rl_papers_with_envs += 1
                if len(sample_rl_papers) < 10:  # Collect samples
                    sample_rl_papers.append({
                        'title': title,
                        'matches': rl_matches[:5],  # First 5 matches
                        'description': desc_text[:100] + '...'
                    })
        
        except Exception as e:
            continue
    
    print(f"\\nRESULTS:")
    print(f"Papers processed: {processed}")
    print(f"Original RL papers (datasets only): {original_rl_count}")
    print(f"RL papers with environments: {rl_papers_with_envs}")
    print(f"Improvement: +{rl_papers_with_envs - original_rl_count} papers")
    
    if original_rl_count > 0:
        improvement_pct = ((rl_papers_with_envs - original_rl_count) / original_rl_count) * 100
        print(f"Percentage improvement: {improvement_pct:+.1f}%")
    
    print(f"\\nSample RL papers found:")
    for i, paper in enumerate(sample_rl_papers):
        print(f"  {i+1}. {paper['title'][:60]}...")
        print(f"      RL keywords: {', '.join(paper['matches'])}")
        print()
    
    # Quick comparison with research domain classification
    with open('mila_domain_taxonomy.json', 'r') as f:
        research_data = json.load(f)
    
    research_rl_count = research_data['category_stats'].get('Reinforcement Learning & Robotics', 0)
    total_research = sum(research_data['category_stats'].values())
    
    research_rl_pct = research_rl_count / total_research * 100
    enhanced_rl_pct = rl_papers_with_envs / processed * 100
    
    print(f"\\nCOMPARISON:")
    print(f"Research domain RL: {research_rl_count} papers ({research_rl_pct:.1f}%)")
    print(f"Enhanced RL (envs): {rl_papers_with_envs} papers ({enhanced_rl_pct:.1f}%)")
    
    if abs(research_rl_pct - enhanced_rl_pct) < 5:
        print("\\n✅ AGREEMENT: Enhanced analysis aligns with research domains")
        print("   Your challenge was correct - environments matter for RL!")
    else:
        print("\\n❌ DISAGREEMENT: Still significant gap between methods")
    
    return {
        'original_rl_datasets': original_rl_count,
        'enhanced_rl_envs': rl_papers_with_envs,
        'research_rl': research_rl_count,
        'improvement': rl_papers_with_envs - original_rl_count
    }

if __name__ == "__main__":
    results = quick_environment_analysis()