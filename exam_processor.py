"""
OMR Exam Processor for Production Website
Handles OMR sheet processing with automatic grading and review flagging
"""

import os
from omr_scanner import detect_bubbles
from typing import Dict, List, Optional, Tuple
import json
from datetime import datetime


class ExamProcessor:
    """Process OMR sheets for exam website with intelligent review flagging"""
    
    def __init__(self, answer_key: Dict[int, int], config: Optional[Dict] = None):
        """
        Initialize processor with answer key and configuration
        
        Args:
            answer_key: {question_num: correct_option} for all 40 questions
            config: Optional configuration overrides
        """
        self.answer_key = answer_key
        self.config = config or {}
        
        # Default configuration
        self.HIGH_CONFIDENCE = self.config.get('high_confidence', 75)
        self.MEDIUM_CONFIDENCE = self.config.get('medium_confidence', 60)
        self.MAX_REVIEW_QUESTIONS = self.config.get('max_review_questions', 3)
        self.MARKS_PER_QUESTION = self.config.get('marks_per_question', 1)
        self.NEGATIVE_MARKING = self.config.get('negative_marking', False)
        self.NEGATIVE_MARKS = self.config.get('negative_marks', -0.25)
    
    def process_sheet(self, image_path: str, student_id: str, 
                     save_debug: bool = False) -> Dict:
        """
        Process a single OMR sheet with comprehensive analysis
        
        Returns complete result dictionary with status, scores, and flags
        """
        try:
            # Scan the sheet
            debug_path = f"debug_{student_id}.jpg" if save_debug else None
            answers, flags, raw_data, confidence = detect_bubbles(
                image_path, debug_out=debug_path
            )
            
            # Grade the answers
            grading_result = self._grade_answers(answers, confidence)
            
            # Determine processing status
            status_info = self._determine_status(flags, confidence)
            
            # Compile complete result
            result = {
                'status': status_info['status'],
                'student_id': student_id,
                'timestamp': datetime.now().isoformat(),
                
                # Grading results
                'score': grading_result['score'],
                'total': grading_result['total'],
                'percentage': grading_result['percentage'],
                'correct_count': len(grading_result['correct']),
                'wrong_count': len(grading_result['wrong']),
                'unanswered_count': len(grading_result['unanswered']),
                
                # Answers and analysis
                'answers': answers,
                'correct_answers': grading_result['correct'],
                'wrong_answers': grading_result['wrong'],
                'unanswered': grading_result['unanswered'],
                
                # Confidence analysis
                'average_confidence': status_info['avg_confidence'],
                'high_confidence_count': status_info['high_conf_count'],
                'medium_confidence_count': status_info['medium_conf_count'],
                'low_confidence_count': status_info['low_conf_count'],
                
                # Review information
                'needs_review': status_info['needs_review'],
                'review_questions': status_info['review_questions'],
                'flags': flags,
                'confidence_scores': confidence,
                
                # Status messages
                'message': status_info['message'],
                'review_reason': status_info['review_reason'],
                
                # Raw data (optional)
                'raw_data': raw_data if self.config.get('include_raw', False) else None
            }
            
            return result
            
        except Exception as e:
            return {
                'status': 'error',
                'student_id': student_id,
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'error_type': type(e).__name__,
                'message': 'Failed to process OMR sheet. Please check image quality and try again.'
            }
    
    def _grade_answers(self, answers: Dict[int, Optional[int]], 
                      confidence: Dict[int, float]) -> Dict:
        """Grade student answers against answer key"""
        score = 0.0
        correct = []
        wrong = []
        unanswered = []
        
        for q_num in range(1, 41):
            correct_option = self.answer_key.get(q_num)
            student_answer = answers.get(q_num)
            
            if student_answer is None:
                unanswered.append(q_num)
            elif correct_option is None:
                # Question not in answer key (shouldn't happen)
                continue
            elif student_answer == correct_option:
                score += self.MARKS_PER_QUESTION
                correct.append(q_num)
            else:
                if self.NEGATIVE_MARKING:
                    score += self.NEGATIVE_MARKS
                wrong.append(q_num)
        
        total_marks = len(self.answer_key) * self.MARKS_PER_QUESTION
        percentage = round((score / total_marks) * 100, 2) if total_marks > 0 else 0
        
        return {
            'score': score,
            'total': len(self.answer_key),
            'percentage': percentage,
            'correct': correct,
            'wrong': wrong,
            'unanswered': unanswered
        }
    
    def _determine_status(self, flags: Dict[int, str], 
                         confidence: Dict[int, float]) -> Dict:
        """Determine processing status and review requirements"""
        
        # Categorize by confidence
        high_conf = []
        medium_conf = []
        low_conf = []
        
        for q in range(1, 41):
            conf = confidence.get(q, 0)
            if conf >= self.HIGH_CONFIDENCE:
                high_conf.append(q)
            elif conf >= self.MEDIUM_CONFIDENCE:
                medium_conf.append(q)
            else:
                low_conf.append(q)
        
        # Questions needing review
        review_questions = []
        for q, flag in flags.items():
            if flag in ['low_confidence', 'multi_mark', 'row_smudged']:
                if q not in review_questions:
                    review_questions.append(q)
        
        # Calculate average confidence
        avg_confidence = round(sum(confidence.values()) / 40, 1) if confidence else 0
        
        # Determine overall status
        if len(review_questions) == 0:
            status = 'success'
            message = 'Sheet processed successfully with high confidence'
            review_reason = None
            needs_review = False
            
        elif len(review_questions) <= self.MAX_REVIEW_QUESTIONS:
            status = 'partial_review'
            message = f'Sheet processed successfully. {len(review_questions)} questions flagged for review'
            review_reason = f'{len(review_questions)} questions have low confidence or multiple marks'
            needs_review = True
            
        else:
            status = 'manual_review'
            message = f'Sheet requires manual review. {len(review_questions)} questions uncertain'
            review_reason = f'Too many uncertain questions ({len(review_questions)}). Manual review recommended'
            needs_review = True
        
        return {
            'status': status,
            'message': message,
            'needs_review': needs_review,
            'review_reason': review_reason,
            'review_questions': sorted(review_questions),
            'avg_confidence': avg_confidence,
            'high_conf_count': len(high_conf),
            'medium_conf_count': len(medium_conf),
            'low_conf_count': len(low_conf)
        }
    
    def process_batch(self, submissions: List[Tuple[str, str]], 
                     save_debug: bool = False) -> Dict:
        """
        Process multiple sheets and return batch results
        
        Args:
            submissions: List of (image_path, student_id) tuples
            save_debug: Whether to save debug images
        
        Returns:
            Dictionary with batch statistics and individual results
        """
        results = []
        stats = {
            'total': len(submissions),
            'success': 0,
            'partial_review': 0,
            'manual_review': 0,
            'errors': 0
        }
        
        for img_path, student_id in submissions:
            result = self.process_sheet(img_path, student_id, save_debug)
            results.append(result)
            
            # Update statistics
            status = result.get('status', 'error')
            if status in stats:
                stats[status] += 1
            else:
                stats['errors'] += 1
        
        # Calculate batch metrics
        avg_scores = [r['score'] for r in results if 'score' in r]
        avg_confidence = [r['average_confidence'] for r in results 
                         if 'average_confidence' in r]
        
        return {
            'batch_stats': {
                **stats,
                'average_score': round(sum(avg_scores) / len(avg_scores), 2) if avg_scores else 0,
                'average_confidence': round(sum(avg_confidence) / len(avg_confidence), 1) if avg_confidence else 0,
                'success_rate': round((stats['success'] / stats['total']) * 100, 1) if stats['total'] > 0 else 0
            },
            'results': results
        }
    
    def export_to_csv(self, results: List[Dict], output_path: str):
        """Export results to CSV file"""
        import csv
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header
            header = ['Student ID', 'Status', 'Score', 'Total', 'Percentage', 
                     'Confidence', 'Correct', 'Wrong', 'Unanswered', 'Review Questions']
            writer.writerow(header)
            
            # Data rows
            for result in results:
                if result['status'] != 'error':
                    row = [
                        result['student_id'],
                        result['status'],
                        result['score'],
                        result['total'],
                        result['percentage'],
                        result['average_confidence'],
                        result['correct_count'],
                        result['wrong_count'],
                        result['unanswered_count'],
                        ', '.join(map(str, result.get('review_questions', [])))
                    ]
                    writer.writerow(row)


# Example usage
if __name__ == '__main__':
    # Example answer key (replace with actual)
    answer_key = {
        1: 2, 2: 3, 3: 1, 4: 4, 5: 2, 6: 3, 7: 1, 8: 2, 9: 4, 10: 3,
        11: 1, 12: 2, 13: 3, 14: 4, 15: 1, 16: 2, 17: 3, 18: 4, 19: 1, 20: 2,
        21: 3, 22: 4, 23: 1, 24: 2, 25: 3, 26: 4, 27: 1, 28: 2, 29: 3, 30: 4,
        31: 1, 32: 2, 33: 3, 34: 4, 35: 1, 36: 2, 37: 3, 38: 4, 39: 1, 40: 2
    }
    
    # Initialize processor
    processor = ExamProcessor(answer_key)
    
    # Process single sheet
    result = processor.process_sheet('sample_sheet.jpg', 'STUDENT001', save_debug=True)
    print(json.dumps(result, indent=2))
