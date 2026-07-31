import json
import os

def main():
    # Load results/scores.json, extract benign samples (y_true == 0)
    scores_path = os.path.join('results', 'scores.json')
    with open(scores_path, 'r', encoding='utf-8') as f:
        scores_data = json.load(f)
        
    y_true_all = scores_data.get('y_true', [])
    score_all = scores_data.get('score', [])
    
    benign_scores = []
    for yt, s in zip(y_true_all, score_all):
        if yt == 0:
            benign_scores.append(s)
            
    print(f"Extracted {len(benign_scores)} benign scores from scores.json")
    
    # Calculate predictions for "full" configuration
    benign_preds = [1 if s >= 0.5 else 0 for s in benign_scores]
    
    # Load results/lolo_preds.json
    lolo_path = os.path.join('results', 'lolo_preds.json')
    with open(lolo_path, 'r', encoding='utf-8') as f:
        lolo_data = json.load(f)
        
    configs = lolo_data.get('configs', {})
    # For each config, append the benign samples
    for config_name, config_data in configs.items():
        if not isinstance(config_data, dict):
            continue
        
        if 'y_true' in config_data and 'y_pred' in config_data and 'family' in config_data:
            config_data['y_true'].extend([0] * len(benign_scores))
            config_data['family'].extend(["benign"] * len(benign_scores))
            # Append identical predictions for all configs for benign samples
            config_data['y_pred'].extend(benign_preds)
            
    # Save back to results/lolo_preds.json
    with open(lolo_path, 'w', encoding='utf-8') as f:
        json.dump(lolo_data, f, indent=2)
        
    # Print per-config FP and TN counts for benign samples
    print("\nBenign Samples Metrics:")
    for config_name, config_data in configs.items():
        if not isinstance(config_data, dict):
            continue
        
        fp = 0
        tn = 0
        yt_list = config_data.get('y_true', [])
        yp_list = config_data.get('y_pred', [])
        for yt, yp in zip(yt_list, yp_list):
            if yt == 0:
                if yp == 1:
                    fp += 1
                elif yp == 0:
                    tn += 1
                    
        print(f"Config: {config_name:<10} | FP: {fp}, TN: {tn}")

if __name__ == '__main__':
    main()
