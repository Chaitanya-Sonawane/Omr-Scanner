import sys, json
sys.path.insert(0, '.')
from omr_engine import scan_image, load_template

template = load_template()
img_path = sys.argv[1] if len(sys.argv) > 1 else '../../debug_adrian1.jpg'
result = scan_image(img_path, template)
print("META:", json.dumps(result['meta'], indent=2, default=str))
print("\nQUESTIONS:")
for q in result['questions']:
    print(f"  Q{q['q']:2d}: option={q['option']} status={q['status']} conf={q['confidence']:.1f}")
