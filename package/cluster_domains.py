#!/usr/bin/env python3
"""
Cluster heterogeneous research domains into main research areas.
Uses domain names, justifications, and quotes for semantic clustering.
"""

import json
import pandas as pd
from collections import defaultdict, Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def load_domain_data():
    """Load extracted domain data."""
    with open('domain_extraction_raw.json', 'r') as f:
        return json.load(f)

def create_domain_text_features(domains_data):
    """Create text features combining domain names, justifications, and quotes."""
    
    all_domains = domains_data['all_domains']
    
    # Group by unique domain names
    domain_groups = defaultdict(list)
    for domain in all_domains:
        domain_name = domain['domain_name']
        if domain_name:
            domain_groups[domain_name].append(domain)
    
    print(f"Found {len(domain_groups)} unique domain names")
    
    # Create text features for each unique domain
    domain_features = []
    
    for domain_name, domain_instances in domain_groups.items():
        # Combine all text from instances of this domain
        combined_text_parts = []
        
        # Add domain name (weighted more heavily)
        combined_text_parts.extend([domain_name] * 3)
        
        # Add justifications and quotes
        for instance in domain_instances:
            if instance.get('justification'):
                combined_text_parts.append(instance['justification'])
            if instance.get('quote'):
                combined_text_parts.append(instance['quote'])
        
        combined_text = ' '.join(combined_text_parts)
        
        domain_features.append({
            'domain_name': domain_name,
            'combined_text': combined_text,
            'instance_count': len(domain_instances),
            'instances': domain_instances
        })
    
    return domain_features

def cluster_domains_semantic(domain_features, n_clusters=8):
    """Perform semantic clustering of domains."""
    
    # Extract text for vectorization
    texts = [df['combined_text'] for df in domain_features]
    domain_names = [df['domain_name'] for df in domain_features]
    
    # TF-IDF vectorization
    vectorizer = TfidfVectorizer(
        max_features=1000,
        stop_words='english',
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.8
    )
    
    X = vectorizer.fit_transform(texts)
    
    # K-means clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(X)
    
    # Organize results
    clusters = defaultdict(list)
    for i, (domain_name, label) in enumerate(zip(domain_names, cluster_labels)):
        clusters[label].append({
            'domain_name': domain_name,
            'instance_count': domain_features[i]['instance_count'],
            'combined_text': domain_features[i]['combined_text'][:200] + '...',
            'instances': domain_features[i]['instances']
        })
    
    return clusters, vectorizer, X, kmeans

def manual_domain_mapping():
    """Create manual mapping of domains to main research areas."""
    
    # Standard ML/AI research areas
    main_areas = {
        'Computer Vision': [
            'computer vision', 'image', 'visual', 'medical imaging', 
            'segmentation', 'detection', 'classification', 'mri', 'ultrasound',
            'spinal cord', 'healthcare informatics'
        ],
        'Natural Language Processing': [
            'nlp', 'language', 'text', 'linguistic', 'translation', 
            'sentiment', 'dialogue', 'question answering'
        ],
        'Reinforcement Learning': [
            'reinforcement learning', 'rl', 'policy', 'reward', 'agent',
            'bipedal locomotion', 'robotics', 'imitation learning', 'control'
        ],
        'Deep Learning & Neural Networks': [
            'deep learning', 'neural network', 'cnn', 'rnn', 'lstm',
            'transformer', 'attention', 'autoencoder'
        ],
        'Graph Learning': [
            'graph neural networks', 'graph', 'network', 'node', 'edge',
            'graph signal processing', 'graph transformers'
        ],
        'Optimization & Operations Research': [
            'optimization', 'combinatorial optimization', 'scheduling',
            'job-shop scheduling', 'network design', 'linear programming'
        ],
        'Software Engineering & Systems': [
            'software engineering', 'bug', 'testing', 'automated game testing',
            'reproducibility', 'systems', 'distributed'
        ],
        'Scientific Computing & Applications': [
            'astrophysics', 'gravitational lensing', 'physics', 'astronomy',
            'pharmacoeconomics', 'mobile health', 'scientific'
        ]
    }
    
    return main_areas

def map_domains_to_areas(domain_features):
    """Map domains to main research areas using keyword matching."""
    
    main_areas = manual_domain_mapping()
    domain_mapping = {}
    unmapped_domains = []
    
    for domain_feature in domain_features:
        domain_name = domain_feature['domain_name'].lower()
        combined_text = domain_feature['combined_text'].lower()
        
        mapped = False
        for area, keywords in main_areas.items():
            for keyword in keywords:
                if keyword in domain_name or keyword in combined_text:
                    domain_mapping[domain_feature['domain_name']] = area
                    mapped = True
                    break
            if mapped:
                break
        
        if not mapped:
            unmapped_domains.append(domain_feature['domain_name'])
    
    return domain_mapping, unmapped_domains, main_areas

def analyze_domain_clusters():
    """Main analysis function."""
    
    print("=== DOMAIN CLUSTERING ANALYSIS ===\\n")
    
    # Load data
    domains_data = load_domain_data()
    domain_features = create_domain_text_features(domains_data)
    
    # Manual mapping approach
    print("1. MANUAL KEYWORD MAPPING")
    domain_mapping, unmapped, main_areas = map_domains_to_areas(domain_features)
    
    # Show results by area
    area_counts = defaultdict(list)
    for domain_name, area in domain_mapping.items():
        # Find instance count
        instance_count = next(df['instance_count'] for df in domain_features if df['domain_name'] == domain_name)
        area_counts[area].append((domain_name, instance_count))
    
    print("\\nResearch Areas with Domain Mapping:")
    total_papers = 0
    for area, domains in area_counts.items():
        paper_count = sum(count for _, count in domains)
        total_papers += paper_count
        print(f"\\n{area} ({paper_count} papers):")
        for domain_name, count in sorted(domains, key=lambda x: x[1], reverse=True):
            print(f"  - {domain_name}: {count} papers")
    
    print(f"\\nUnmapped domains ({len(unmapped)}):")
    for domain in unmapped:
        instance_count = next(df['instance_count'] for df in domain_features if df['domain_name'] == domain)
        print(f"  - {domain}: {instance_count} papers")
    
    # Semantic clustering approach
    print("\\n\\n2. SEMANTIC CLUSTERING")
    clusters, vectorizer, X, kmeans = cluster_domains_semantic(domain_features, n_clusters=6)
    
    print("\\nSemantic Clusters:")
    for cluster_id, domains in clusters.items():
        total_instances = sum(d['instance_count'] for d in domains)
        print(f"\\nCluster {cluster_id} ({total_instances} papers):")
        for domain in sorted(domains, key=lambda x: x['instance_count'], reverse=True):
            print(f"  - {domain['domain_name']}: {domain['instance_count']} papers")
    
    # Save results
    results = {
        'manual_mapping': {
            'area_counts': {area: [(name, count) for name, count in domains] 
                           for area, domains in area_counts.items()},
            'unmapped_domains': unmapped,
            'main_areas_definition': main_areas
        },
        'semantic_clustering': {
            'clusters': {str(k): v for k, v in clusters.items()},
            'n_clusters': len(clusters)
        },
        'domain_features': domain_features
    }
    
    with open('domain_clusters.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\\nResults saved to domain_clusters.json")
    print(f"Total papers analyzed: {total_papers}")
    
    return results

if __name__ == "__main__":
    results = analyze_domain_clusters()