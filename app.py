import os, sqlite3, secrets
from pathlib import Path
from functools import wraps
from flask import Flask, request, redirect, url_for, session, flash, render_template_string, abort
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get("DATA_DIR", str(ROOT)))
DATA.mkdir(parents=True, exist_ok=True)
UPLOADS = DATA / "uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)
DB = DATA / "store.db"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    raise RuntimeError("Render ortam degiskenlerinde ADMIN_PASSWORD ayarlanmamis.")
PASSWORD_HASH = generate_password_hash(ADMIN_PASSWORD)
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config.update(MAX_CONTENT_LENGTH=5*1024*1024, SESSION_COOKIE_HTTPONLY=True,
                  SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=True)
ALLOWED = {"png","jpg","jpeg","webp","gif"}
TG = "Denktinee"

def connect():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
with connect() as c:
    c.execute("""CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '', price TEXT NOT NULL, image TEXT NOT NULL DEFAULT '')""")

def admin(fn):
    @wraps(fn)
    def w(*a,**k):
        if not session.get("admin"): return redirect(url_for("login"))
        return fn(*a,**k)
    return w

def csrf():
    if "_csrf" not in session: session["_csrf"]=secrets.token_urlsafe(24)
    return session["_csrf"]

@app.before_request
def protect():
    if request.method=="POST":
        t=request.form.get("_csrf","")
        if not session.get("_csrf") or not secrets.compare_digest(t,session["_csrf"]): abort(400)

BASE = """<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Gökø Store</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');
:root{--bg:#090a10;--panel:#121420;--text:#f5f5fb;--muted:#9da1b5;--line:#292c3d;--purple:#9b7cff}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 50% -20%,#282044,transparent 48%),var(--bg);color:var(--text);font-family:'DM Sans',Arial,sans-serif;min-height:100vh}
header{height:70px;padding:0 max(calc((100% - 1080px)/2),20px);display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #ffffff18}
.brand{font-size:22px;font-weight:800;color:white;text-decoration:none}.brand span,h1 span{color:var(--purple)}nav{display:flex;gap:20px}nav a{color:var(--muted);text-decoration:none}
main{max-width:1080px;margin:auto;padding:35px 20px 70px}.hero{padding:55px 0}.eyebrow{color:var(--purple);font-size:11px;font-weight:800;letter-spacing:2px}.hero h1{font-size:clamp(42px,7vw,72px);margin:10px 0;line-height:1}.muted,p{color:var(--muted);line-height:1.65}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:18px}.card,.panel{background:var(--panel);border:1px solid var(--line);border-radius:16px;overflow:hidden}.pic,.placeholder{height:210px;width:100%;object-fit:cover;background:linear-gradient(135deg,#282044,#111522)}.placeholder{display:grid;place-items:center;color:var(--purple);font-size:44px;font-weight:800}.info{padding:17px}.info h3{margin:0}.bottom,.head,.actions,.item{display:flex;align-items:center;justify-content:space-between;gap:10px}.bottom{margin-top:18px}.btn{display:inline-block;border:0;border-radius:9px;background:var(--purple);color:#100d1b;text-decoration:none;padding:11px 15px;font-weight:800;cursor:pointer;font-size:13px}.secondary{background:#292c3d;color:white}.danger{background:#542638;color:white}.small{padding:8px 11px}.panel{max-width:540px;margin:30px auto;padding:25px}.panel h1{margin:5px 0 15px}label{display:block;margin:13px 0 6px;font-weight:700;font-size:13px}input,textarea{width:100%;padding:12px;border:1px solid var(--line);border-radius:9px;background:#0c0e17;color:white;font:inherit}button.full{width:100%;margin-top:18px}.list{border:1px solid var(--line);border-radius:14px;overflow:hidden}.item{padding:13px 16px;background:var(--panel);border-bottom:1px solid var(--line)}.item:last-child{border:0}.item p{margin:3px 0}.flash{background:#28203c;border:1px solid #57458d;padding:8px 13px;border-radius:9px}.empty{text-align:center;padding:45px 15px}.actions form{margin:0}footer{text-align:center;color:#656a80;border-top:1px solid #ffffff12;padding:22px;font-size:12px}
@media(max-width:600px){.head{align-items:flex-start;flex-direction:column}.item{align-items:flex-start;flex-direction:column}.actions{width:100%}.actions>*{flex:1}.actions .btn{width:100%;text-align:center}}
</style></head><body><header><a class="brand" href="/">Gökø <span>Store</span></a><nav><a href="/">Mağaza</a><a href="/admin">Admin</a></nav></header><main>{% with ms=get_flashed_messages() %}{% if ms %}<div class="flash">{% for m in ms %}{{m}}{% endfor %}</div>{% endif %}{% endwith %}{% block body %}{% endblock %}</main><footer>© Gökø Store</footer></body></html>"""
# For a truly one-file app, use inline templates via DictLoader.
from jinja2 import DictLoader
templates = {
"base": BASE,
"home": """{% extends 'base' %}{% block body %}<section class="hero"><div class="eyebrow">ONLINE STORE</div><h1>Tarzını <span>keşfet.</span></h1><p>Gökø Store'a hoş geldin. Ürünleri incele, satın almak için Telegram'dan bize ulaş.</p></section><div class="head"><div><div class="eyebrow">KOLEKSİYON</div><h2>Ürünlerimiz</h2></div><p>{{products|length}} ürün</p></div>{% if products %}<div class="grid">{% for p in products %}<article class="card">{% if p.image %}<img class="pic" src="/uploads/{{p.image}}">{% else %}<div class="placeholder">Gökø</div>{% endif %}<div class="info"><h3>{{p.name}}</h3><p>{{p.description}}</p><div class="bottom"><b>{{p.price}}</b><a class="btn" href="https://t.me/Denktinee" target="_blank" rel="noopener">Satın Al ↗</a></div></div></article>{% endfor %}</div>{% else %}<div class="panel empty"><h3>Henüz ürün eklenmedi</h3><p>İlk ürününü admin panelinden ekleyebilirsin.</p><a class="btn" href="/admin/login">Admin paneli</a></div>{% endif %}{% endblock %}""",
"login": """{% extends 'base' %}{% block body %}<div class="panel"><div class="eyebrow">YÖNETİCİ GİRİŞİ</div><h1>Admin Paneli</h1><p>Yönetici şifreni gir.</p><form method="post"><input type="hidden" name="_csrf" value="{{token}}"><label>Şifre</label><input type="password" name="password" required><button class="btn full">Giriş yap</button></form></div>{% endblock %}""",
"dash": """{% extends 'base' %}{% block body %}<div class="head"><div><div class="eyebrow">YÖNETİM</div><h1>Ürünler</h1><p>Ürün ekle, düzenle veya sil.</p></div><div class="actions"><a class="btn" href="/admin/new">+ Ürün ekle</a><form method="post" action="/admin/logout"><input type="hidden" name="_csrf" value="{{token}}"><button class="btn secondary">Çıkış</button></form></div></div><div class="list">{% for p in products %}<div class="item"><div><b>{{p.name}}</b><p>{{p.price}}</p></div><div class="actions"><a class="btn secondary small" href="/admin/edit/{{p.id}}">Düzenle</a><form method="post" action="/admin/delete/{{p.id}}" onsubmit="return confirm('Ürün silinsin mi?')"><input type="hidden" name="_csrf" value="{{token}}"><button class="btn danger small">Sil</button></form></div></div>{% else %}<div class="empty">Henüz ürün yok.</div>{% endfor %}</div>{% endblock %}""",
"form": """{% extends 'base' %}{% block body %}<div class="panel"><div class="eyebrow">ÜRÜN YÖNETİMİ</div><h1>{{'Ürünü düzenle' if product else 'Yeni ürün ekle'}}</h1><form method="post" enctype="multipart/form-data"><input type="hidden" name="_csrf" value="{{token}}"><label>Ürün adı</label><input name="name" required value="{{product.name if product else ''}}"><label>Fiyat</label><input name="price" required value="{{product.price if product else ''}}"><label>Açıklama</label><textarea name="description" rows="4">{{product.description if product else ''}}</textarea><label>Fotoğraf</label><input type="file" name="image" accept=".png,.jpg,.jpeg,.webp,.gif"><p><button class="btn">Kaydet</button> <a class="btn secondary" href="/admin">Vazgeç</a></p></form></div>{% endblock %}"""
}
app.jinja_loader = DictLoader(templates)

@app.route("/")
def home():
    with connect() as c: products=c.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    return render_template_string("{% extends 'home' %}", products=products)

@app.route("/uploads/<path:name>")
def uploaded(name):
    from flask import send_from_directory
    return send_from_directory(UPLOADS, name)

@app.route("/admin/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        if check_password_hash(PASSWORD_HASH,request.form.get("password","")):
            session.clear(); session["admin"]=True
            return redirect("/admin")
        flash("Şifre yanlış.")
    return render_template_string("{% extends 'login' %}", token=csrf())

@app.route("/admin")
@admin
def dashboard():
    with connect() as c: products=c.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    return render_template_string("{% extends 'dash' %}", products=products, token=csrf())

@app.route("/admin/logout",methods=["POST"])
@admin
def logout():
    session.clear(); return redirect("/")

@app.route("/admin/new",methods=["GET","POST"])
@admin
def new():
    if request.method=="POST": return save_product()
    return render_template_string("{% extends 'form' %}", product=None, token=csrf())

@app.route("/admin/edit/<int:pid>",methods=["GET","POST"])
@admin
def edit(pid):
    with connect() as c: p=c.execute("SELECT * FROM products WHERE id=?",(pid,)).fetchone()
    if not p: abort(404)
    if request.method=="POST": return save_product(pid,p)
    return render_template_string("{% extends 'form' %}", product=p, token=csrf())

def save_product(pid=None, old=None):
    name=request.form.get("name","").strip(); price=request.form.get("price","").strip()
    desc=request.form.get("description","").strip()
    if not name or not price:
        flash("Ürün adı ve fiyat zorunlu."); return redirect(request.path)
    image=old["image"] if old else ""
    f=request.files.get("image")
    if f and f.filename:
        ext=f.filename.rsplit(".",1)[-1].lower() if "." in f.filename else ""
        if ext not in ALLOWED: flash("PNG, JPG, WEBP veya GIF görsel yükle."); return redirect(request.path)
        image=secrets.token_hex(8)+"_"+secure_filename(f.filename); f.save(UPLOADS/image)
    with connect() as c:
        if pid: c.execute("UPDATE products SET name=?,description=?,price=?,image=? WHERE id=?",(name,desc,price,image,pid))
        else: c.execute("INSERT INTO products(name,description,price,image) VALUES(?,?,?,?)",(name,desc,price,image))
    flash("Ürün kaydedildi."); return redirect("/admin")

@app.route("/admin/delete/<int:pid>",methods=["POST"])
@admin
def delete(pid):
    with connect() as c:
        row=c.execute("SELECT image FROM products WHERE id=?",(pid,)).fetchone()
        c.execute("DELETE FROM products WHERE id=?",(pid,))
    if row and row["image"]:
        try: (UPLOADS/row["image"]).unlink(missing_ok=True)
        except OSError: pass
    flash("Ürün silindi."); return redirect("/admin")

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT","5000")))
