<script>
  // The page's two inputs (docs/framework_prototype.md §2.3 item 2, §3, probe A4): plain
  // `select`s of the data-bice contract, their options read from the page's queries, that write
  // Evidence's own input store through its public setter — so that Evidence's queries, which name
  // `inputs.canal` and `inputs.mes`, run again on a change. Evidence's Dropdown is no `select`.
  import { getInputSetter } from '@evidence-dev/sdk/utils/svelte';

  export let canais = [];
  export let meses = [];

  const setCanal = getInputSetter('canal');
  const setMes = getInputSetter('mes');
  let canal = '%';
  let mes = null;

  $: channels = [...(canais ?? [])].map((r) => r.sales_channel_name);
  $: months = [...(meses ?? [])].map((r) => r.year_month);
  $: if (months.length && mes === null) mes = months[months.length - 1];
  $: setCanal(canal, canal === '%' ? 'todos' : canal, canal);
  $: if (mes !== null) setMes(mes, mes, mes);
</script>

<label>Canal
  <select data-bice="filter" bind:value={canal}>
    <option value="%">todos</option>
    {#each channels as c}<option value={c}>{c}</option>{/each}
  </select>
</label>
<label>Mês do detalhe
  <select data-bice="month" bind:value={mes}>
    {#each months as m}<option value={m}>{m}</option>{/each}
  </select>
</label>
