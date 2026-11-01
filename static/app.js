document.querySelectorAll('[data-search]').forEach(input => input.addEventListener('input', () => {
  document.querySelectorAll('#'+input.dataset.search+' tbody tr').forEach(row => row.hidden=!row.textContent.toLowerCase().includes(input.value.toLowerCase()));
}));
document.querySelectorAll('[data-print]').forEach(button=>button.addEventListener('click',()=>window.print()));
document.querySelectorAll('input[name=scope]').forEach(radio=>radio.addEventListener('change',()=>{
  ['department','year','semester'].forEach(key=>radio.form.elements[key].value=radio.dataset[key]);
}));
document.querySelectorAll('[data-generating]').forEach(form=>form.addEventListener('submit',()=>{
  const button=form.querySelector('button');button.disabled=true;button.textContent='Finding a place for every subject…';
}));
const dialog=document.getElementById('confirm-dialog');let pending;
document.querySelectorAll('form[data-confirm]').forEach(form=>form.addEventListener('submit',event=>{
  event.preventDefault();pending=form;document.getElementById('confirm-message').textContent=form.dataset.confirm;dialog.showModal();
}));
document.getElementById('confirm-cancel').addEventListener('click',()=>dialog.close());
document.getElementById('confirm-accept').addEventListener('click',()=>{dialog.close();pending.submit();});
