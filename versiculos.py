"""
Módulo de Versículos Diarios de la Biblia
Catatumbo Digital - Concejo Municipal Bolivariano de Maracaibo

Proporciona una amplia selección de 31 versículos de sabiduría, fortaleza, 
paz y bendición para rotar automáticamente cada día del año.
"""

from datetime import datetime

VERSICULOS_DIARIOS = [
    # 1. Sabiduría y Conocimiento
    ("Proverbios 2:6", "Porque Jehová da la sabiduría, y de su boca viene el conocimiento y la inteligencia."),
    ("Santiago 1:5", "Y si alguno de vosotros tiene falta de sabiduría, pídala a Dios, el cual da a todos abundantemente y sin reproche, y le será dada."),
    ("Proverbios 3:5-6", "Fíate de Jehová de todo tu corazón, y no te apoyes en tu propia prudencia. Reconócelo en todos tus caminos, y él enderezará tus veredas."),
    ("Salmos 119:105", "Lámpara es a mis pies tu palabra, y lumbrera a mi camino."),
    ("Proverbios 16:3", "Encomienda a Jehová tus obras, y tus pensamientos serán afirmados."),
    
    # 2. Fortaleza y Valentía
    ("Filipenses 4:13", "Todo lo puedo en Cristo que me fortalece."),
    ("Josué 1:9", "Mira que te mando que te esfuerces y seas valiente; no temas ni desmayes, porque Jehová tu Dios estará contigo en dondequiera que vayas."),
    ("Isaías 41:10", "No temas, porque yo estoy contigo; no desmayes, porque yo soy tu Dios que te esfuerzo; siempre te ayudaré, siempre te sustentaré."),
    ("Salmos 27:1", "Jehová es mi luz y mi salvación; ¿de quién temeré? Jehová es la fortaleza de mi vida; ¿de quién he de atemorizarme?"),
    ("Salmos 46:1", "Dios es nuestro amparo y fortaleza, nuestro pronto auxilio en las tribulaciones."),

    # 3. Paz y Confianza
    ("Salmos 23:1", "Jehová es mi pastor; nada me faltará."),
    ("Juan 14:27", "La paz os dejo, mi paz os doy; yo no os la doy como el mundo la da. No se turbe vuestro corazón, ni tenga miedo."),
    ("Filipenses 4:6-7", "Por nada estéis afanosos, sino sean conocidas vuestras peticiones delante de Dios en toda oración y ruego, con acción de gracias. Y la paz de Dios guardará vuestros corazones."),
    ("Salmos 91:1-2", "El que habita al abrigo del Altísimo morará bajo la sombra del Omnipotente. Diré yo a Jehová: Esperanza mía, y castillo mío; mi Dios, en quien confiaré."),
    ("Jeremías 29:11", "Porque yo sé los pensamientos que tengo acerca de vosotros, dice Jehová, pensamientos de paz, y no de mal, para daros el fin que esperáis."),

    # 4. Trabajo, Diligencia y Servicio
    ("Colosenses 3:23", "Y todo lo que hagáis, hacedlo de corazón, como para el Señor y no para los hombres."),
    ("Salmos 90:17", "Sea la luz de Jehová nuestro Dios sobre nosotros, y la obra de nuestras manos confirma sobre nosotros."),
    ("Gálatas 6:9", "No nos cansemos, pues, de hacer bien; porque a su tiempo segaremos, si no desmayamos."),
    ("1 Corintios 15:58", "Estad firmes y constantes, creciendo en la obra del Señor siempre, sabiendo que vuestro trabajo en el Señor no es en vano."),
    ("Mateo 5:16", "Así alumbre vuestra luz delante de los hombres, para que vean vuestras buenas obras, y glorifiquen a vuestro Padre que está en los cielos."),

    # 5. Amor, Bondad y Esperanza
    ("Lamentaciones 3:22-23", "Por la misericordia de Jehová no hemos sido consumidos, porque nunca decayeron sus misericordias. Nuevas son cada mañana; grande es tu fidelidad."),
    ("Romanos 8:28", "Y sabemos que a los que aman a Dios, todas las cosas les ayudan a bien, esto es, a los que conforme a su propósito son llamados."),
    ("Miqueas 6:8", "Oh hombre, él te ha declarado lo que es bueno, y qué pide Jehová de ti: solamente hacer justicia, y amar misericordia, y humillarte ante tu Dios."),
    ("Salmos 37:4", "Deléitate asimismo en Jehová, y él te concederá las peticiones de tu corazón."),
    ("Proverbios 4:23", "Sobre toda cosa guardada, guarda tu corazón; porque de él mana la vida."),

    # 6. Alabanza y Bendición
    ("Salmos 103:1-2", "Bendice, alma mía, a Jehová, y bendiga todo mi ser su santo nombre. Bendice, alma mía, a Jehová, y no olvides ninguno de sus beneficios."),
    ("Salmos 118:24", "Este es el día que hizo Jehová; nos gozaremos y alegraremos en él."),
    ("Números 6:24-26", "Jehová te bendiga, y te guarde; Jehová haga resplandecer su rostro sobre ti, y tenga de ti misericordia; Jehová alce sobre ti su rostro, y ponga en ti paz."),
    ("Salmos 34:1", "Bendeciré a Jehová en todo tiempo; su alabanza estará de continuo en mi boca."),
    ("Hebreos 11:1", "Es, pues, la fe la certeza de lo que se espera, la convicción de lo que no se ve."),
    ("Salmos 121:1-2", "Alzaré mis ojos a los montes; ¿de dónde vendrá mi socorro? Mi socorro viene de Jehová, que hizo los cielos y la tierra.")
]

def obtener_versiculo_del_dia(fecha=None):
    """
    Retorna (referencia, texto) para el día actual.
    Utiliza el día juliano del año (o número ordinal) para que cada día 
    del calendario cambie de forma automática, garantizando un versículo distinto cada día.
    """
    if fecha is None:
        fecha = datetime.now()
    
    # Calcular índice único basado en el día del año (1..366)
    dia_del_ano = fecha.timetuple().tm_yday
    indice = dia_del_ano % len(VERSICULOS_DIARIOS)
    
    return VERSICULOS_DIARIOS[indice]

if __name__ == '__main__':
    ref, txt = obtener_versiculo_del_dia()
    print(f"Versículo de hoy: \"{txt}\" — {ref}")
