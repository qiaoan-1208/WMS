import sqlite3
from flask import Flask, flash, redirect, render_template, request, url_for

app = Flask(__name__)
app.secret_key = "wms_secret_key"  # 用于 Flask 的提示信息（flash）


# 数据库初始化函数
def init_db():
    conn = sqlite3.connect("wms.db")
    cursor = conn.cursor()
    # 创建库存表
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory (
            sku TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            quantity INTEGER DEFAULT 0,
            location TEXT
        )
    """
    )
    # 创建出入库流水表
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT,
            name TEXT,
            type TEXT, -- '入库' 或 '出库'
            quantity INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    conn.commit()
    conn.close()


# 辅助函数：获取数据库连接
def get_db_connection():
    conn = sqlite3.connect("wms.db")
    conn.row_factory = sqlite3.Row  # 允许通过列名访问数据
    return conn


# 1. 首页：查看当前库存
@app.route("/")
def index():
    conn = get_db_connection()
    items = conn.execute("SELECT * FROM inventory").fetchall()
    conn.close()
    return render_template("index.html", items=items)


# 2. 入库操作
@app.route("/in", methods=["GET", "POST"])
def in_stock():
    if request.method == "POST":
        sku = request.form["sku"].strip()
        name = request.form["name"].strip()
        quantity = int(request.form["quantity"])
        location = request.form["location"].strip()

        if not sku or not name or quantity <= 0:
            flash("请输入正确的商品信息和数量！", "danger")
            return redirect(url_for("in_stock"))

        conn = get_db_connection()
        # 检查商品是否已存在
        item = conn.execute(
            "SELECT * FROM inventory WHERE sku = ?", (sku,)
        ).fetchone()

        if item:
            # 更新已有商品库存
            conn.execute(
                "UPDATE inventory SET quantity = quantity + ?, location = ? WHERE sku = ?",
                (quantity, location, sku),
            )
        else:
            # 插入新商品
            conn.execute(
                "INSERT INTO inventory (sku, name, quantity, location) VALUES (?, ?, ?, ?)",
                (sku, name, quantity, location),
            )

        # 记录流水
        conn.execute(
            "INSERT INTO stock_logs (sku, name, type, quantity) VALUES (?, ?, '入库', ?)",
            (sku, name, quantity),
        )
        conn.commit()
        conn.close()

        flash(f"商品【{name}】入库成功！数量：{quantity}", "success")
        return redirect(url_for("index"))

    return render_template("in_stock.html")


# 3. 出库操作
@app.route("/out", methods=["GET", "POST"])
def out_stock():
    if request.method == "POST":
        sku = request.form["sku"].strip()
        quantity = int(request.form["quantity"])

        if not sku or quantity <= 0:
            flash("请输入正确的货号和出库数量！", "danger")
            return redirect(url_for("out_stock"))

        conn = get_db_connection()
        item = conn.execute(
            "SELECT * FROM inventory WHERE sku = ?", (sku,)
        ).fetchone()

        if not item:
            flash("未找到该货号的商品！", "danger")
            conn.close()
            return redirect(url_for("out_stock"))

        if item["quantity"] < quantity:
            flash(
                f"库存不足！当前库存仅剩: {item['quantity']}", "danger"
            )
            conn.close()
            return redirect(url_for("out_stock"))

        # 扣减库存
        conn.execute(
            "UPDATE inventory SET quantity = quantity - ? WHERE sku = ?",
            (quantity, sku),
        )
        # 记录流水
        conn.execute(
            "INSERT INTO stock_logs (sku, name, type, quantity) VALUES (?, ?, '出库', ?)",
            (sku, item["name"], quantity),
        )
        conn.commit()
        conn.close()

        flash(f"商品【{item['name']}】出库成功！数量：{quantity}", "success")
        return redirect(url_for("index"))

    return render_template("out_stock.html")


# 4. 流水日志
@app.route("/logs")
def logs():
    conn = get_db_connection()
    logs = conn.execute(
        "SELECT * FROM stock_logs ORDER BY timestamp DESC"
    ).fetchall()
    conn.close()
    return render_template("logs.html", logs=logs)


if __name__ == "__main__":
    init_db()  # 程序启动时初始化数据库
    app.run(debug=True)