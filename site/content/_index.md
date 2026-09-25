<div class="custom-card info-card" style="margin-top: 40px; text-align: left;">

&#x20;   <h3 id="daily-pv-title" style="margin-top: 0; margin-bottom: 15px;">🌟 Günün Phrasal Verb'ü: Yükleniyor...</h3>

&#x20;   <p id="daily-pv-meaning" style="margin-bottom: 15px; color: #475569; line-height: 1.6;">Kelimeler taranıyor, lütfen bekleyin...</p>

&#x20;   <a id="daily-pv-link" href="#" style="display: inline-block; padding: 8px 16px; background-color: var(--primary-orange); color: white; border-radius: 6px; text-decoration: none; font-weight: bold;">Kelimeyi İncele →</a>

</div>



<script>

document.addEventListener("DOMContentLoaded", function() {

&#x20;   // Sitenin kendi gizli veritabanını okuyoruz (Tüm kelimeleriniz burada)

&#x20;   fetch('/index.json')

&#x20;   .then(response => response.json())

&#x20;   .then(data => {

&#x20;       // Sadece phrasal verb sayfalarını filtrele (arama vs. sayfalarını hariç tut)

&#x20;       const words = data.filter(item => item.permalink \&\& item.permalink.includes('/phrasal-verbs/') \&\& !item.permalink.includes('ara'));

&#x20;       

&#x20;       if(words.length > 0) {

&#x20;           // Yılın kaçıncı gününde olduğumuzu bulup ona göre kelime seç (Her gün otomatik değişir)

&#x20;           const today = new Date();

&#x20;           const dayIndex = Math.floor((today - new Date(today.getFullYear(), 0, 0)) / 1000 / 60 / 60 / 24);

&#x20;           const selected = words\[dayIndex % words.length];

&#x20;           

&#x20;           // Başlıktaki "Ne Demek?" gibi fazlalıkları atıp temiz İngilizce kelimeyi al

&#x20;           const pvName = selected.title.split(" Ne Demek?")\[0];

&#x20;           document.getElementById("daily-pv-title").innerText = "🌟 Günün Phrasal Verb'ü: " + pvName;

&#x20;           

&#x20;           // İçeriğin ilk 130 karakterini alarak temiz bir önizleme (snippet) oluştur

&#x20;           let snippet = selected.content.substring(0, 130).replace(/#/g, '').replace(/\\\*/g, '').trim();

&#x20;           document.getElementById("daily-pv-meaning").innerHTML = snippet + "...";

&#x20;           

&#x20;           document.getElementById("daily-pv-link").href = selected.permalink;

&#x20;       }

&#x20;   })

&#x20;   .catch(error => console.error("Kelime yüklenirken hata oluştu:", error));

});

</script>

