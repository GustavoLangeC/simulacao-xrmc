# Experimento mínimo XRMC: PMMA com uma perfuração

Este projeto simula a aquisição física e exporta imagem e referência geométrica.
O segmentador é executado separadamente e recebe apenas a imagem para detectar;
a referência entra depois, na avaliação.

## Escopo científico

O experimento representa uma placa retangular de PMMA de 25 mm, uma perfuração
passante de 10 mm, um filtro de alumínio de 2 mm, uma fonte pontual e um
detector plano a 1 m da fonte. O objeto está a 1,25 cm do detector.

O espectro inicial é deliberadamente **monoenergético de 50 keV**. Ele é útil
para validar geometria, atenuação relativa e leitura do XRMC, mas não equivale
a uma aquisição clínica de 81 kVp. A modelagem de espectro, anodo, resposta do
detector, dose/mAs, espalhamento real e pós-processamento fica para uma fase de
calibração posterior.

## Executar

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
./instalar_xrmc_local.sh  # somente se .deps/xrmc/bin/xrmc ainda não existir
XRMC_PYTHON=.venv/bin/python ./executar_minimo.sh
```

O comando executa `minimo_pmmaa_furo/input.dat` e grava:

- `output/image.dat`: saída binária XRMC, float64 e cabeçalho de 60 bytes;
- `output/image.npy`: matriz `256 x 256` convertida sem normalização;
- `output/image.png`: prévia visual em escala de cinza, com contraste exibido
  entre os percentis 1 e 99; é apenas visualização e não substitui o NPY;
- `output/manifest.json`: parâmetros e versão do experimento.
- `output/verdade_simulada.npz`: rótulos da perfuração projetada, calculados
  da geometria do cenário e **nunca fornecidos ao detector**;
- `output/verdade_simulada.json`: método, hashes da imagem e do manifesto,
  contagem de pixels e nota sobre a incerteza da borda.

O teste de sucesso é físico e simples: a transmissão média no centro da
perfuração deve ser maior que a do PMMA ao redor. `validar_minimo.py` executa
essa checagem (com ROIs fixas **somente para validar esta geometria conhecida**)
e imprime a razão de transmissões. Isso não valida a reprodução quantitativa
do equipamento Philips nem a segmentação.

## Avaliar com o segmentador

No repositório irmão `segmentador-fantomas`, execute:

```bash
venv/bin/python -m segmentador_fantomas.avaliar_simulacao \
  --imagem ../simulacao-xrmc/minimo_pmmaa_furo/output/image.npy \
  --referencia ../simulacao-xrmc/minimo_pmmaa_furo/output/verdade_simulada.npz \
  --saida resultados/avaliacao_simulada
```

O comando gera métricas TP/FP/FN e IoU, máscaras, medições CSV e relatório HTML.
O vínculo SHA-256 impede avaliar uma referência criada para outra imagem.
O modelo geométrico usa raios centrais e centros de pixel; amostragem e
penumbra podem produzir diferenças de borda. O cenário atual tem um único
furo passante e não demonstra generalização do detector.

## Cenários analíticos de estresse

`gerar_cenario_analitico.py` cria imagens `float64` e referências NPZ para
testar o software sem executar XRMC. Há três configurações em `cenarios/`:

| Configuração | Objetivo |
| --- | --- |
| `quatro_formas.json` | Círculo, retângulo, elipse e L com profundidades de 5, 10, 15 e 20 mm, ruído baixo e gradiente. |
| `baixo_contraste.json` | Duas regiões rasas com ruído e gradiente fortes. |
| `saturacao.json` | Duas regiões com sinal limitado artificialmente por um teto. |

Exemplo, dentro deste repositório:

```bash
.venv/bin/python gerar_cenario_analitico.py \
  --config cenarios/quatro_formas.json --saida cenarios_gerados/quatro_formas
```

Depois execute `segmentador_fantomas.avaliar_simulacao` no repositório irmão,
apontando `--imagem` para `image.npy` e `--referencia` para
`verdade_simulada.npz` da pasta gerada. O manifesto registra a geometria,
o ruído, o gradiente, a semente e os parâmetros do modelo; a referência
registra profundidades somente para a **avaliação posterior**.

O sinal ilustrativo é `S=(S_PMMA+gradiente)·exp(μ·profundidade_cm)+ruído`,
com eventual corte por `clip_max`. O coeficiente `μ=0,24 cm⁻¹` e os níveis
numéricos são parâmetros de demonstração, sem calibração para os DICOMs ou
para o equipamento do TCC. Esses cenários revelam falhas e limites do
detector; não são evidência de desempenho clínico nem equivalem ao XRMC.

## Estrutura de coordenadas e unidades

O XRMC usa centímetros. A fonte está em `(0, -100, 0)` cm e o detector no
plano `y=0`, portanto a distância fonte-detector é 100 cm. O feixe percorre a
direção `+y`; `x` é a direção horizontal da imagem e `z`, a vertical.

## Dependência local

O executável esperado fica em `.deps/xrmc/bin/xrmc`; a biblioteca `xraylib`
local fica em `.deps/xraylib`. Esses componentes não alteram a instalação do
sistema. Se faltarem, use:

```bash
./instalar_xrmc_local.sh
```

O instalador é destinado ao Debian/Trixie deste computador e usa a release
XRMC 6.7.0. Ele não instala Geant4.
