from aisearch.thread_reader import extract_refs


def test_extract_refs_finds_github_issue_pr_and_commit():
    refs = extract_refs(
        """
        Related to #12 and owner/other#13.
        See https://github.com/acme/project/pull/14.
        Fixed by https://github.com/acme/project/commit/abcdef1234567890.
        More context: https://example.com/post.
        """,
        source_url="https://github.com/acme/project/issues/1",
        repo_context="acme/project",
    )

    urls = {ref.url for ref in refs}

    assert "https://github.com/acme/project/issues/12" in urls
    assert "https://github.com/owner/other/issues/13" in urls
    assert "https://github.com/acme/project/pull/14" in urls
    assert "https://github.com/acme/project/commit/abcdef1234567890" in urls
    assert "https://example.com/post" in urls
