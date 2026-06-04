from flask import Flask, jsonify
from flask_cors import CORS
import simpy
import random

app = Flask(__name__)
CORS(app)

def run_bank_sim():
    env = simpy.Environment()
    results = []
    # هنا نضع منطق الكود الخاص بكِ
    # سأختصر لكِ المنطق ليعطي بيانات سريعة للـ Dashboard
    for i in range(1, 11):
        results.append({
            "name": f"Müşteri {i}",
            "wait": round(random.uniform(1, 10), 2)
        })
    return results

@app.route('/api/data')
def get_data():
    data = run_bank_sim()
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
    