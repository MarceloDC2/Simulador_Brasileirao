def TiraAcentos(Texto):
   T = Texto
   CAcento = "àáâãäèéêëìíîïòóôõöùúûüÀÁÂÃÄÈÉÊËÌÍÎÒÓÔÕÖÙÚÛÜçÇñÑ"
   SAcento = "aaaaaeeeeiiiiooooouuuuAAAAAEEEEIIIOOOOOUUUUcCnN"
   Count = 0
   for a in CAcento:
      if Texto.find(a) > -1:
         T = T.replace(a,SAcento[Count])
      Count+=1
   return T
#TiraAcentos

def RemoveCaracteresNaoImprimiveis(Texto):
   if Texto =='' or Texto == None:
    return ''
   Texto = str(Texto)
   newstring = ''
   for a in Texto: 
    if (a.isprintable()) == False: 
      newstring+=' '
    else: 
      newstring+= a
   newstring = newstring.strip()
   return newstring
# RemoveCaracteresNaoImprimiveis

def LimpaTexto(S):
  return TiraAcentos(RemoveCaracteresNaoImprimiveis(S)).upper().strip().replace('"',"'")
# LimpaTexto