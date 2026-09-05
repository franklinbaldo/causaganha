/**
 * Liga um <input> ao elemento de dica visual da busca da home (#1127):
 * a cada digitação, mostra se a entrada abrirá o dossiê do processo
 * (/processo) ou uma busca de publicações (/publicacoes), reusando a
 * classificação de describeHeroSearchMode. Sem JS, `hint` permanece com o
 * atributo `hidden` do markup estático — o formulário continua funcional.
 */
import { describeHeroSearchMode } from './processoCnj';

export function attachHeroSearchHint(input: HTMLInputElement, hint: HTMLElement): () => void {
  const render = () => {
    const { mode, label } = describeHeroSearchMode(input.value);
    hint.textContent = label;
    hint.hidden = mode === null;
    if (mode === null) {
      delete hint.dataset.mode;
    } else {
      hint.dataset.mode = mode;
    }
  };

  render();
  input.addEventListener('input', render);
  return () => input.removeEventListener('input', render);
}
