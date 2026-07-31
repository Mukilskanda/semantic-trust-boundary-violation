import sys
import os
import json

def main():
    # Add b3 inference script to sys path
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'b3', 'solution_stb', 'b3_semantic_gate'))
    from inference import get_predictor

    # 1. Read b3_eval/data/id_split.jsonl, extract all entries where label == 0 (benign samples).
    benign_samples = []
    total_samples = 0
    
    input_file = os.path.join('b3_eval', 'data', 'id_split.jsonl')
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            total_samples += 1
            entry = json.loads(line)
            if entry.get('label') == 0:
                benign_samples.append(entry)

    # 2. Run each entry's text field through the B3 inference pipeline.
    model_path = os.path.join('b3', 'solution_stb', 'b3_semantic_gate', 'model', 'semantic_gate_v3')
    predictor = get_predictor(model_path)
    
    texts = [sample['text'] for sample in benign_samples]
    results = predictor.predict(texts)
    
    new_scores = []
    for res in results:
        if res.label == "MALICIOUS_SEMANTIC_MANIPULATION":
            score = res.confidence
        else:
            score = 1.0 - res.confidence
        new_scores.append(float(score))
        
    # 3. Load results/scores.json (has y_true and score lists).
    scores_path = os.path.join('results', 'scores.json')
    with open(scores_path, 'r', encoding='utf-8') as f:
        scores_data = json.load(f)
        
    y_true = scores_data.get('y_true', [])
    score_list = scores_data.get('score', [])
    
    # 4. Append 27 zeros to y_true and the 27 new scores to score. Save back to results/scores.json.
    y_true.extend([0] * len(new_scores))
    score_list.extend(new_scores)
    
    with open(scores_path, 'w', encoding='utf-8') as f:
        json.dump({"y_true": y_true, "score": score_list}, f, indent=2)
        
    # 5. Print a summary: how many samples total, how many benign, new TP/FP/TN/FN at threshold 0.5.
    print(f"Total samples: {total_samples}")
    print(f"Benign samples: {len(benign_samples)}")
    
    tp = fp = tn = fn = 0
    for yt, s in zip(y_true, score_list):
        pred = 1 if s >= 0.5 else 0
        if yt == 1 and pred == 1:
            tp += 1
        elif yt == 0 and pred == 1:
            fp += 1
        elif yt == 0 and pred == 0:
            tn += 1
        elif yt == 1 and pred == 0:
            fn += 1
            
    print(f"New Metrics at threshold 0.5 -> TP: {tp}, FP: {fp}, TN: {tn}, FN: {fn}")

if __name__ == '__main__':
    main()
