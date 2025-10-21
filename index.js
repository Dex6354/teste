/**
 * Bem-vindo ao seu Worker!
 *
 * Este worker atua como uma API para buscar dados do seu KV Namespace.
 * - Ele escuta por requisições GET.
 * - Acessa o KV Namespace vinculado com o nome de variável "SHOPPING_LIST_KV".
 * - Busca o valor associado à chave "shopping_list".
 * - Retorna os dados como uma resposta JSON.
 * - Inclui cabeçalhos CORS para permitir que sua página do GitHub o acesse.
 */
export default {
  async fetch(request, env, ctx) {
    // Define os cabeçalhos para a resposta.
    // O 'Access-Control-Allow-Origin' é ESSENCIAL para permitir que
    // a página do GitHub acesse este worker.
    const headers = new Headers({
      'Content-Type': 'application/json;charset=UTF-8',
      'Access-Control-Allow-Origin': '*', // Permite acesso de qualquer origem
      'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
    });

    // Lida com requisições "preflight" do CORS, comuns em navegadores.
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers });
    }

    try {
      // 1. Acessa o KV Namespace. `env.SHOPPING_LIST_KV` é como o worker
      //    se refere ao seu KV, graças à vinculação que faremos no painel.
      // 2. Busca o valor da chave 'shopping_list'.
      // 3. Pede para o Cloudflare já interpretar o resultado como JSON.
      const shoppingListData = await env.SHOPPING_LIST_KV.get('shopping_list', { type: 'json' });

      // Se a chave não existir no KV, o valor será `null`.
      if (shoppingListData === null) {
        return new Response(
          JSON.stringify({ error: "A chave 'shopping_list' não foi encontrada no KV." }),
          {
            status: 404,
            headers,
          }
        );
      }

      // Se encontrou, retorna os dados com sucesso (status 200).
      return new Response(JSON.stringify(shoppingListData), {
        status: 200,
        headers,
      });

    } catch (err) {
      // Em caso de qualquer outro erro, retorna uma mensagem de erro.
      console.error(err);
      return new Response(
        JSON.stringify({ error: 'Erro interno no servidor do Worker.' }),
        {
          status: 500,
          headers,
        }
      );
    }
  },
};
