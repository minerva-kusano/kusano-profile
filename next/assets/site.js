/* 弧牛忘路――編書牛事：共通スクリプト */

/* すべて展開／折りたたむ（旧ページと同じ動き） */
function toggleAll(btn){
  const all=document.querySelectorAll('details');
  const anyOpen=[...all].some(d=>d.open);
  all.forEach(d=>d.open=!anyOpen);
  btn.textContent=anyOpen?'▼ すべて展開':'▲ すべて折りたたむ';
}
(function(){
  /* 折りたたみが二つ以上あるページでだけボタンを出す */
  var btn=document.querySelector('.expand-all');
  if(btn && document.querySelectorAll('details').length>=2){btn.hidden=false;}

  /* #〜 で折りたたみの中を指されたら開いてから移動する */
  function openTarget(){
    var id=decodeURIComponent(location.hash.slice(1)); if(!id) return;
    var el=document.getElementById(id); if(!el) return;
    var d=el.closest('details'), touched=false;
    while(d){ if(!d.open){d.open=true;touched=true;} d=d.parentElement&&d.parentElement.closest('details'); }
    if(touched){el.scrollIntoView();}
  }
  window.addEventListener('hashchange',openTarget); openTarget();
})();

/* ---- GA4：問い合わせ行動の分析 ----
   イベント名 contact_click と引数は旧ページのまま。
   複数ページになったので、閲覧時間・スクロール・開いた大項目の記録を
   同じタブのあいだ（sessionStorage）ページをまたいで引き継ぐ。 */
(function(){
  var KEY='kusano_profile_ga', st=null;
  try{st=JSON.parse(sessionStorage.getItem(KEY)||'null');}catch(e){}
  if(!st||typeof st.start!=='number'){st={start:Date.now(),maxScroll:0,opened:[]};}
  function save(){try{sessionStorage.setItem(KEY,JSON.stringify(st));}catch(e){}}

  /* 大項目を何個開いたか：旧ページの六つの大項目に対応する章を訪れたら数える */
  var section=document.documentElement.getAttribute('data-section');
  if(section && st.opened.indexOf(section)<0){st.opened.push(section);}
  save();

  /* 最大スクロール率を記録 */
  window.addEventListener('scroll', function(){
    var doc=document.documentElement;
    var scrollableHeight=doc.scrollHeight-window.innerHeight;
    if(scrollableHeight>0){
      var currentPercent=Math.round((window.scrollY/scrollableHeight)*100);
      if(currentPercent>st.maxScroll){st.maxScroll=currentPercent;save();}
    }
  },{passive:true});

  /* 問い合わせクリック */
  window.trackContact=function(position){
    var elapsedSeconds=Math.round((Date.now()-st.start)/1000);
    var readerStage='mid';
    if(position==='top' && elapsedSeconds<30 && st.opened.length===0){
      readerStage='early';
    }else if(st.maxScroll>=75 || st.opened.length>=2 || elapsedSeconds>=90){
      readerStage='deep';
    }
    if(typeof gtag==='function'){
      gtag('event','contact_click',{
        contact_position: position,
        reader_stage: readerStage,
        elapsed_seconds: elapsedSeconds,
        max_scroll_percent: st.maxScroll,
        opened_sections_count: st.opened.length
      });
    }
  };
})();
