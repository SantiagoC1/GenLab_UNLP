from app.knowledge import load_knowledge, search


def test_loads_all_topics_and_ignores_the_readme():
    topics = {doc.topic for doc in load_knowledge()}
    assert "Exoma clínico" in topics
    assert "Proceso del estudio" in topics
    assert "Patologías lisosomales" in topics
    assert len(topics) == 10


def test_every_topic_has_a_status_and_closes_with_the_doctor():
    for doc in load_knowledge():
        assert doc.status in ("borrador", "validado")
        assert "médico tratante" in doc.body


def test_search_ignores_accents_plurals_and_case():
    docs = load_knowledge()
    assert search("EXOMAS CLINICOS", docs)[0][0].topic == "Exoma clínico"


def test_search_finds_nothing_for_unrelated_text():
    assert search("receta de empanadas", load_knowledge()) == []
