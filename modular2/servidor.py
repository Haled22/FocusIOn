from flask import Flask, request, jsonify

app = Flask(__name__)
@app.route('/track', methods=['POST'])
def track():
    data = request.json
    x = data.get("x")
    y = data.get("y")
    area_trabajo = data.get("area")
    x_max = area_trabajo[0][0]
    act_w = area_trabajo[0][2]
    y_max = area_trabajo[0][1]
    act_h = area_trabajo[0][3]
    inside = ((x_max < x < x_max +act_w) and \
            (y_max < y < y_max + act_h))

    if inside:
        return jsonify({"status": "No distraido"})
    else:
        return jsonify({"status": "Distraido"})
       


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)