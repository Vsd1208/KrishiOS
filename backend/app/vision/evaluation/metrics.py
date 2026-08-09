"""Evaluation metrics for vision model performance."""

from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class EvaluationMetrics:
    """Calculates accuracy, precision, recall, and F1 for vision models."""
    
    # ground_truth -> model_prediction -> count
    confusion_matrix: dict[str, dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    
    total_samples: int = 0
    correct_samples: int = 0

    def add_result(self, ground_truth: str, prediction: str) -> None:
        """Add a single prediction result."""
        self.total_samples += 1
        if ground_truth == prediction:
            self.correct_samples += 1
            
        self.confusion_matrix[ground_truth][prediction] += 1

    @property
    def accuracy(self) -> float:
        if self.total_samples == 0:
            return 0.0
        return self.correct_samples / self.total_samples
        
    def precision(self, class_name: str) -> float:
        # True Positives / (True Positives + False Positives)
        tp = self.confusion_matrix[class_name][class_name]
        
        fp = 0
        for gt, preds in self.confusion_matrix.items():
            if gt != class_name:
                fp += preds.get(class_name, 0)
                
        if (tp + fp) == 0:
            return 0.0
        return tp / (tp + fp)

    def recall(self, class_name: str) -> float:
        # True Positives / (True Positives + False Negatives)
        tp = self.confusion_matrix[class_name][class_name]
        
        fn = 0
        for pred, count in self.confusion_matrix[class_name].items():
            if pred != class_name:
                fn += count
                
        if (tp + fn) == 0:
            return 0.0
        return tp / (tp + fn)

    def f1_score(self, class_name: str) -> float:
        p = self.precision(class_name)
        r = self.recall(class_name)
        
        if (p + r) == 0:
            return 0.0
        return 2 * (p * r) / (p + r)
