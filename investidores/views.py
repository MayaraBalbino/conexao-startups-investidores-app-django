from django.shortcuts import render, redirect
from empresarios.models import Empresas, Documento, Metricas, PropostaInvestimento
from django.contrib import messages
from django.contrib.messages import constants
from django.http import HttpResponse, Http404

# Create your views here.

def sugestao(request):
    if not request.user.is_authenticated:
        return redirect('/usuarios/logar')
    
    if request.method == 'GET':
        return render(request, 'sugestao.html', {'areas': Empresas.area_choices})
    elif request.method == 'POST':
        tipo = request.POST.get('tipo')
        area = request.POST.getlist('area') #para campos do tipo multiple(podem selecionar mais de uma opção)
        valor = request.POST.get('valor')

        if tipo == 'C':
            empresas = Empresas.objects.filter(tempo_existencia='+5').filter(estagio='E') #filtrar apenas os selecionados
        elif tipo == 'D':
            empresas = Empresas.objects.filter(tempo_existencia__in=['-6', '+6', '+1']).exclude(estagio='E') # __in indica que ele so vai pegar os que estao dentro da lista, exclude ele exclui o opção e pega todas as outras


        empresas = empresas.filter(area__in=area)

        empresas_selecionadas = []

        for empresa in empresas:
            percentual = float(valor) * 100 / float(empresa.valuation)
            if percentual >= 1:
                empresas_selecionadas.append(empresa)
            else:
                messages.add_message(request, constants.ERROR, 'O valor que voce deseja investir nao é o suficiente')
                return redirect('/investidores/sugestao')

        return render(request, 'sugestao.html', {'areas': Empresas.area_choices, 'empresas': empresas_selecionadas})
        
def ver_empresa(request, id):
    empresa = Empresas.objects.get(id=id)   
    metricas = Metricas.objects.filter(empresa=empresa)
    documentos = Documento.objects.filter(empresa=empresa)
    proposta_investimento = PropostaInvestimento.objects.filter(empresa=empresa).filter(status='PA')

    percentual_vendido = 0
    for pi in proposta_investimento:
        percentual_vendido += pi.percentual

    limiar = 0.8 * empresa.percentual_equity
    concretizado = False
    if percentual_vendido >= limiar:
        concretizado = True

    percentual_disponivel = empresa.percentual_equity - percentual_vendido
    return render(request, 'ver_empresa.html', {'empresa': empresa, 'documentos': documentos, 'metricas': metricas, 'percentual_vendido': int(percentual_vendido), 'concretizado': concretizado, 'percentual_disponivel': percentual_disponivel})

def realizar_proposta(request, id):
    empresa = Empresas.objects.get(id=id)
    valor = request.POST.get('valor')
    percentual = request.POST.get('percentual')

    propostas_aceitas = PropostaInvestimento.objects.filter(empresa=empresa).filter(status='PA')

    total = 0
    for pa in propostas_aceitas:
        total += pa.percentual

    if total + float(percentual) > empresa.percentual_equity:
        messages.add_message(request, constants.ERROR, 'O percentual solicitado ultrapassa o percentual maximo')
        return redirect(f'/investidores/ver_empresa/{id}')

    valuation = 100 * int(valor) / int(percentual)
    if valuation < int(empresa.valuation / 2):
        messages.add_message(request, constants.ERROR, f'O valuation proposto foi R${valuation} e deve ser no mínimo R${empresa.valuation:.2f}')
        return redirect(f'/investidores/ver_empresa/{id}')
    
    
    pi = PropostaInvestimento(
            valor=valor,
            percentual=percentual,
            empresa=empresa,
            investidor=request.user,
        )
        
    pi.save()
    
    return redirect(f'/investidores/assinar_contrato/{pi.id}')

def assinar_contrato(request, id):
    pi = PropostaInvestimento.objects.get(id=id)

    if pi.status != 'AS':
        raise Http404()

    if request.method == 'GET':
        return render(request, 'assinar_contrato.html', {'pi': pi})
    elif request.method == 'POST':
        selfie = request.FILES.get('selfie')
        rg = request.FILES.get('rg')
        print(request.FILES)

        if not selfie or not rg:
            messages.add_message(request, constants.ERROR, 'Os arquivos precisam ser anexados')
            return redirect(f'/investidores/assinar_contrato/{pi.id}')

        #realizar autenticação selfie e rg
        
        pi.selfie = selfie
        pi.rg = rg
        pi.status = 'PE'
        pi.save()

        messages.add_message(request, constants.SUCCESS, f'Contrato assinado com sucesso, sua proposta foi enviada a empresa.')
        return redirect(f'/investidores/ver_empresa/{pi.empresa.id}')



