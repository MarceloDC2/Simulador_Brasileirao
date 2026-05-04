# URL da GLOBO
# https://api.globoesporte.globo.com/tabela/d1a37fa4-e948-43a6-ba53-ab24ab3a45b1/fase/fase-unica-campeonato-brasileiro-2026/rodada/2/jogos/
# URL da CBF:
# https://www.cbf.com.br/api/proxy?path=/jogos/tabela-detalhada/campeonato/12606
# URL da Gazeta Esportiva
# https://footstats.gazetaesportiva.com/campeonatos/brasileiro-serie-a-2025/partidas/

import streamlit as st
import requests
from random import random
import pandas as pd
import matplotlib.pyplot as plt
import Utilidades
from pprint import pprint

# ---------- Configurações iniciais ----------
RODADA_FINAL = 38
ANO          = '2026'

class Times():
  def __init__(self):
    self.times = dict()
  # __init__
  
  def pega_um_time(self, nome, zera_valores):
    nome = Utilidades.LimpaTexto(nome)
    if zera_valores:
      self.times[nome] = {
          'partidas_mandante' : 0,
          'vitorias_mandante' : 0,
          'empates_mandante'  : 0,
          'derrotas_mandante' : 0,
          'partidas_visitante': 0,
          'vitorias_visitante': 0,
          'empates_visitante' : 0,
          'derrotas_visitante': 0,
          'pontos': 0.0,
      }
    # endif
    return nome
  # pega_um_time

  def pega_times(self):
    """Pega a lista de times a partir da rodada 1."""
    # url = 'https://www.cbf.com.br/api/proxy?path=/jogos/tabela-detalhada/campeonato/12606'
    url = f'https://api.globoesporte.globo.com/tabela/d1a37fa4-e948-43a6-ba53-ab24ab3a45b1/fase/fase-unica-campeonato-brasileiro-{ANO}/rodada/1/jogos/'
    resp = requests.get(url)
    resp.raise_for_status()
    self.todos_jogos = resp.json()
    
    # rodada_1 = [jogo for jogo in self.todos_jogos if jogo['rodada'] == 1]
    rodada_1 = [jogo for jogo in self.todos_jogos]

    for jogo in rodada_1:
      self.pega_um_time(jogo['equipes']['mandante']['nome_popular'] , zera_valores=True)
      self.pega_um_time(jogo['equipes']['visitante']['nome_popular'], zera_valores=True)
    # next

    for nr_rodada in range(2, 39):
      rodada = str(nr_rodada)
      url = f'https://api.globoesporte.globo.com/tabela/d1a37fa4-e948-43a6-ba53-ab24ab3a45b1/fase/fase-unica-campeonato-brasileiro-{ANO}/rodada/{rodada}/jogos/'
      resp = requests.get(url)
      resp.raise_for_status()
      self.todos_jogos.extend(resp.json())
    # next

    return
  # pega_times

  def executar_simulacao(self, rodada_inicial=1, nr_simulacoes=10000, st_progress_callback=None):

    # Preenche times e obtém jogos pendentes
    jogos_faltantes = self.preenche_times_e_jogos(rodada_inicial)

    # Calcula probabilidades para cada jogo pendente
    for i, jogo in enumerate(jogos_faltantes.jogos):
      mand, vis, _, _, _, _ = jogo
      prob_man, prob_vis, prob_emp = probabilidade_resultado(
        self.times[mand]['vitorias_mandante'], self.times[mand]['empates_mandante'], self.times[mand]['derrotas_mandante'],
        self.times[vis]['vitorias_visitante'], self.times[vis]['empates_visitante'], self.times[vis]['derrotas_visitante']
      )
      jogos_faltantes.jogos[i][2] = prob_man
      jogos_faltantes.jogos[i][3] = prob_man + prob_vis
      jogos_faltantes.jogos[i][4] = prob_man + prob_vis + prob_emp
    # next

    # Simulações Monte Carlo
    resultados = {um_time: [0] * 20 for um_time in self.times}

    for simulacao in range(nr_simulacoes):
      # barra de progresso opcional
      if st_progress_callback and simulacao % max(1, nr_simulacoes // 100) == 0:
          st_progress_callback(simulacao / nr_simulacoes)
      # endif

      dic_pontuacao_simulada = {um_time: self.times[um_time]['pontos'] for um_time in self.times}

      for jogo in jogos_faltantes.jogos:
        mandante, visitante, prob_man, prob_vis, prob_emp, data = jogo
        sorteio = random()
        if sorteio < prob_man:
          dic_pontuacao_simulada[mandante] += 3.01
        elif sorteio < prob_vis:
          dic_pontuacao_simulada[visitante] += 3.01
        else:
          dic_pontuacao_simulada[mandante] += 1
          dic_pontuacao_simulada[visitante] += 1
        # endif
      # next
      colocacao = sorted(dic_pontuacao_simulada.items(), key=lambda um_time: um_time[1], reverse=True)
      for lugar, um_time in enumerate(colocacao):
        resultados[um_time[0]][lugar] += 1
      # next
    # next

    # Retorna dataframe com probabilidades
    df = pd.DataFrame(resultados)
    df.index = df.index + 1
    df_prob = 100 * df / nr_simulacoes
    sorted_columns = df_prob.iloc[0].sort_values(ascending=False).index
    df_prob = df_prob[sorted_columns]
    df_prob = df_prob.round(0).astype(int)
    return df_prob, jogos_faltantes
  # executar_simulacao

  def preenche_times_e_jogos(self, rodada_inicial=1):
    jogos_faltantes = JogosNaoRealizados()

    for rodada, jogo in enumerate(self.todos_jogos):
      if rodada+1 < rodada_inicial: continue

      mandante  = self.pega_um_time(jogo['equipes']['mandante']['nome_popular'] , False)
      visitante = self.pega_um_time(jogo['equipes']['visitante']['nome_popular'], False)

      if jogo['jogo_ja_comecou']:        
        self.times[mandante]['partidas_mandante']   += 1
        self.times[visitante]['partidas_visitante'] += 1

        if int(jogo['placar_oficial_mandante']) == int(jogo['placar_oficial_visitante']):
          self.times[mandante]['empates_mandante'] += 1
          self.times[mandante]['pontos'] += 1
          self.times[visitante]['empates_visitante'] += 1
          self.times[visitante]['pontos'] += 1
        elif int(jogo['placar_oficial_mandante']) > int(jogo['placar_oficial_visitante']):
          self.times[mandante]['vitorias_mandante'] += 1
          self.times[mandante]['pontos'] += 3.01
          self.times[visitante]['derrotas_visitante'] += 1
        else:
          self.times[mandante]['derrotas_mandante'] += 1
          self.times[visitante]['vitorias_visitante'] += 1
          self.times[visitante]['pontos'] += 3.01
        # endif
      else:
        if jogo['data_realizacao'] == None:
          data_partida = '99999999'
        else:
          data_partida = jogo['data_realizacao'][:10]
        # endif
        jogos_faltantes.jogos.append([mandante, visitante, 0.0, 0.0, 0.0, data_partida])        
      # endif
    # next
    jogos_faltantes.jogos = sorted(jogos_faltantes.jogos, key = lambda jogo: jogo[-1])
    return jogos_faltantes
  # preenche_times_e_jogos

# fim classe Times

class JogosNaoRealizados:
  def __init__(self):
    self.jogos = []  # cada item: [mandante, visitante, prob_man, prob_vis_cumul, prob_total_cumul, data_jogo]
  # __init__
#fim classe JogosNaoRealizados

def probabilidade_resultado(vitorias_mandante, empates_mandante, derrotas_mandante,
                            vitorias_visitante, empates_visitante, derrotas_visitante):
    vetor_mandante = [3] * vitorias_mandante + [1] * empates_mandante + [0] * derrotas_mandante
    vetor_visitante = [0] * derrotas_visitante + [1] * empates_visitante + [3] * vitorias_visitante

    nr_comparacoes = min(len(vetor_mandante), len(vetor_visitante))
    if nr_comparacoes == 0:
        # sem histórico suficiente: retornar probabilidades uniformes
        return 0.33, 0.33, 0.34

    prob_mandante = prob_visitante = prob_empate = 0
    for jogo in range(nr_comparacoes):
        if vetor_mandante[jogo] > vetor_visitante[jogo]:
            prob_mandante += 1
        elif vetor_mandante[jogo] < vetor_visitante[jogo]:
            prob_visitante += 1
        else:
            prob_empate += 1

    return prob_mandante / nr_comparacoes, prob_visitante / nr_comparacoes, prob_empate / nr_comparacoes
# probabilidade_resultado

# ---------- Streamlit App ----------

def main():
    def update_progress(p):
      progresso_bar.progress(min(1.0, max(0.0, p)))
    # update_progress

    st.set_page_config(page_title="Simulador do Brasileirão", layout="wide")
    st.title("⚽ Simulador do Brasileirão")
    st.title('base: Globo Esporte')

    with st.sidebar:
      st.header("Configurações")
      # ano = st.number_input("Ano", min_value=2010, max_value=2030, value=2025, step=1)
      rodada_inicial = st.number_input("Rodada inicial (para recalcular a partir de)", min_value=1, max_value=38, value=1, step=1)
      nr_simulacoes = st.number_input("Número de simulações", min_value=100, max_value=20000, value=10000, step=100)
      run = st.button("Executar simulação")
    # end_with

    placeholder_status = st.empty()
    progresso_bar = st.progress(0)

    if run:
      try:
        placeholder_status.info("Buscando e processando dados... (isso pode demorar alguns segundos)")

        times = Times()
        times.pega_times()
        df_prob, jogos_faltantes = times.executar_simulacao(rodada_inicial, nr_simulacoes, st_progress_callback=update_progress)

        placeholder_status.success("Simulação concluída com sucesso!")

        # Mostrar tabela resumida
        st.subheader("Probabilidades de posição (1 a 20)")
        st.dataframe(df_prob)

        # Mostrar gráficos - 20 gráficos, dois por linha
        colors = ['#29681E', '#339523', '#3AC426', '#3FF527',
                  '#27B4F5', '#2A91C4', '#286F94', '#224E68',
                  '#69411A', '#965A1F', '#C47523', '#F59127',
                  '#AC9B25', '#C42126', '#DCC727', '#F5DD27',
                  '#AD261F', '#C52722', '#DD2724', '#F52727'
                 ]
        st.subheader("Gráficos de distribuição por time")
        cols = st.columns(2)
        count = 0
        for time_name in df_prob.columns:
          fig, ax = plt.subplots(figsize=(8, 8))
          # ax.plot(df_prob.index, df_prob[time_name], marker='o')          
          ax.bar(df_prob.index, df_prob[time_name], color=colors)
          ax.set_title(time_name, fontsize=16)
          ax.set_xlabel('Posição')
          ax.set_ylabel('Probabilidade (%)')
          ax.set_xticks(range(1, 21))
          ax.grid(True, linestyle='--', alpha=0.4)
          plt.ylim(0, 100)

          cols[count % 2].pyplot(fig)
          plt.close(fig)
          count += 1
        # next

        # Estatísticas rápidas
        st.subheader("Resumo: probabilidades-chave")
        resumo = pd.DataFrame(index=df_prob.columns)
        resumo['Campeonato (posição 1)'] = df_prob.loc[1]
        resumo['Top4 (soma posições 1-4)'] = df_prob.loc[1:4].sum()
        resumo['Z4 (soma posições 17-20)'] = df_prob.loc[17:20].sum()
        st.table(resumo.sort_values('Campeonato (posição 1)', ascending=False))

        # Probabiidade de cada jogo restante
        st.subheader("Jogos Restantes")
        cols = st.columns(1)
        for jogo in jogos_faltantes.jogos:
          # print(jogo)
          vitoria_mandante  = round(100*(jogo[2]))
          empate            = round(100*(1-jogo[3]))
          vitoria_visitante = round(100*(jogo[3]-jogo[2]))
          total = vitoria_mandante + empate + vitoria_visitante
          if total < 100: empate += 1
          valores = [vitoria_mandante,
                     empate,
                     vitoria_visitante]
          rotulos = [str(valores[0]), str(valores[1]),str(valores[2])]
          # rotulos = ['30', '50', '20']
          cores = ['#0000CD', '#87CEFF', '#6C8631']
          fig, ax = plt.subplots(figsize=(10, 0.5))
          ax.set_xlim(0, 100) # Define o limite do eixo X para o total dos valores
          ax.set_yticks([])    # Remove os ticks do eixo Y para parecer uma linha
          ax.set_frame_on(False)
          ax.set_title(f'{jogo[0]} X {jogo[1]}', pad=1)
          ax.legend(loc='center left', bbox_to_anchor=(1, 0.5)) # Adiciona legenda fora do gráfico
          largura_anterior = 0

          for i, valor in enumerate(valores):
            ax.barh(y=[0], width=valor, left=largura_anterior, color=cores[i], height=0.5, label=rotulos[i])
            largura_anterior += valor
          # endif

          for i, valor in enumerate(valores):
            ax.barh(y=[0], width=1, left=largura_anterior, color=cores[i], label=rotulos[i])
            largura_anterior += valor
          # next
          cols[0].pyplot(fig)
          plt.close(fig)
        # next jogos_faltantes

      except requests.HTTPError as e:
        placeholder_status.error(f"Erro nas requisições HTTP: {e}")
      except Exception as e:
        placeholder_status.error(f"Erro inesperado: {e}")
      # fim_try
    # endif run
# fim main


if __name__ == '__main__':
  main()
  # times = Times()
  # times.pega_times()
  # df_prob = times.executar_simulacao(1, 1000, None)