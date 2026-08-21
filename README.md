# Ağ Gözcüsü

TP-Link TD-W9970 V3 modem üzerindeki cihazları ve anlık ağ kullanımını yerel bir web panelinde gösteren FastAPI uygulaması.

## Özellikler

- Ağa bağlı cihazları IP ve MAC adresleriyle listeler.
- Trafik kullanımını WebSocket üzerinden canlı günceller.
- Cihazlara `BERK-PC`, `Salon TV` gibi kalıcı ve anlaşılır isimler vermeyi sağlar.
- Toplam trafik, çevrimiçi cihaz sayısı ve cihaz bazlı kullanım bilgilerini gösterir.
- Modeme bağlanmadan arayüzü denemek için örnek veri modu içerir.
- Modem parolasını yalnızca yerel `.env` dosyasında tutar.

> [!NOTE]
> TD-W9970 V3'ün kullanılan firmware sürümü cihaz başına indirme ve yükleme değerlerini ayrı ayrı sunmadığı için panel birleşik trafik kullanımını gösterir.

## Desteklenen ortam

Bu entegrasyon aşağıdaki cihazda geliştirilmiştir:

- Modem: TP-Link TD-W9970 V3
- Donanım sürümü: `TD-W9970 v3 00000001`
- Yazılım sürümü: `23.08.17.01006`

Diğer modem ve firmware sürümlerinin CGI oturum açma veya istatistik formatları farklı olabilir.

## Kurulum

Python 3.11 veya daha yeni bir sürüm önerilir.

```powershell
git clone https://github.com/ergunberk/ag-gozcusu.git
cd ag-gozcusu
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Uygulamayı önce örnek verilerle çalıştırabilirsiniz:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Ardından [http://127.0.0.1:8000](http://127.0.0.1:8000) adresini açın.

## Modeme bağlanma

`.env` dosyasındaki alanları kendi modem bilgilerinize göre düzenleyin:

```dotenv
APP_MODE=router
ROUTER_URL=http://192.168.1.1
ROUTER_USERNAME=admin
ROUTER_PASSWORD=modem_paneli_parolaniz
POLL_INTERVAL=5
```

Modem panelindeki trafik istatistiklerinin etkin olması gerekir. `.env` dosyası Git tarafından dışlanır; gerçek parolanızı hiçbir zaman GitHub'a yüklemeyin.

## Testler

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Proje yapısı

```text
app/                 FastAPI uygulaması ve modem bağlantısı
static/              Dashboard arayüzü
tests/               Otomatik testler
.env.example         Güvenli örnek yapılandırma
requirements.txt     Python bağımlılıkları
```

## Gizlilik

Uygulama yerel ağınızda çalışır. Modem giriş bilgileri, keşfedilen cihazlara verdiğiniz özel isimler ve çalışma sırasında oluşan yerel veriler repository'ye dahil edilmez.

## Lisans

Bu proje [MIT Lisansı](LICENSE) ile sunulmaktadır.
