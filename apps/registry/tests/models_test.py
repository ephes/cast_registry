def test_domain_start_deployment(domain):
    deployment_id = domain.start_deployment()
    assert deployment_id == 1
