const menu = document.querySelector('.menu-button');
menu?.addEventListener('click', () => {const open=document.querySelector('.header').classList.toggle('menu-open');menu.setAttribute('aria-expanded', String(open));});
document.querySelectorAll('form[data-confirm]').forEach(form=>form.addEventListener('submit',event=>{if(!confirm(form.dataset.confirm))event.preventDefault();}));
