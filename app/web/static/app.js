// Лёгкая обратная связь на сабмит формы: блокируем кнопку и меняем текст,
// чтобы пользователь видел, что обогащение идёт (синхронный вызов может занять
// несколько секунд при большом батче).
document.addEventListener("submit", (event) => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement)) return;

  const submit = form.querySelector("button[type='submit']");
  if (!submit) return;

  const busyText = submit.dataset.busy;
  if (busyText) {
    submit.dataset.original = submit.textContent;
    submit.textContent = busyText;
  }
  submit.disabled = true;
});
