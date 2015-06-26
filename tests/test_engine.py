"""
Copyright (C) 2012 Haak Saxberg

This file is part of Flowhub, a command-line tool to enable various
Git-based workflows that interacts with GitHub.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

import mock
import pytest

from flowhub.engine import Engine
from flowhub.managers import TagInfo


@pytest.fixture
def repository_structure(id_generator):
    return {
        "name": id_generator(),
        "origin": id_generator(),
        "canon": id_generator(),
        "master": id_generator(),
        "develop": id_generator(),
        "feature": id_generator(),
        "release": id_generator(),
        "hotfix": id_generator(),
    }


class NotARepoSetupTestCase(object):
    def test_setup_abort(self):
        import git
        def raise_call_error(*args, **kwargs):
            raise git.exc.InvalidGitRepositoryError

        with mock.patch("git.Repo.__init__") as patch:
            patch.side_effect = raise_call_error

            with pytest.raises(git.exc.InvalidGitRepositoryError):
                Engine(offline=True)


class EngineTestCase(object):
    @pytest.yield_fixture
    def github(self):
        with mock.patch('flowhub.engine.Github') as gh_mock:
            yield gh_mock

    @pytest.yield_fixture
    def git(self):
        with mock.patch('flowhub.engine.git.Repo') as git_mock:
            yield git_mock

    @pytest.yield_fixture
    def configurator(self):
        with mock.patch('flowhub.engine.Configurator') as conf_mock:
            yield conf_mock

    @pytest.yield_fixture
    def feature_manager(self):
        with mock.patch('flowhub.engine.FeatureManager', autospec=True) as f_mock:
            yield f_mock

    @pytest.yield_fixture
    def release_manager(self):
        with mock.patch('flowhub.engine.ReleaseManager', autospec=True) as f_mock:
            yield f_mock

    @pytest.yield_fixture
    def hotfix_manager(self):
        with mock.patch('flowhub.engine.HotfixManager', autospec=True) as f_mock:
            yield f_mock

    @pytest.yield_fixture
    def pull_manager(self):
        with mock.patch('flowhub.engine.PullRequestManager', autospec=True) as f_mock:
            yield f_mock


class OfflineTestCase(object):
    @pytest.yield_fixture
    def github(self):
        with mock.patch('flowhub.engine.Github') as gh_mock:
            yield gh_mock
            assert gh_mock.call_count == 0

    @pytest.fixture
    def engine(self, git, repository_structure, feature_manager, hotfix_manager, pull_manager, release_manager, configurator):
        engine = Engine(init=True, offline=True)


        engine.setup_repository_structure(
            **repository_structure
        )

        # setup the configurator mock
        for key in ["name", "origin", "canon", "master", "develop"]:
            setattr(
                configurator.return_value.flowhub.structure,
                key,
                repository_structure[key]
            )
        for key in ["feature", "release", "hotfix"]:
            setattr(
                configurator.return_value.flowhub.prefix,
                key,
                repository_structure[key]
            )

        engine = Engine(offline=True)
        feature_manager.assert_has_calls([
            mock.call(
                debug=engine.DEBUG,
                prefix=repository_structure['feature'],
                origin=mock.ANY,
                canon=mock.ANY,
                master=mock.ANY,
                develop=mock.ANY,
                release=mock.ANY,
                hotfix=mock.ANY,
                repo=mock.ANY,
                gh=None,
                offline=True
            ),
        ])

        release_manager.assert_has_calls([
            mock.call(
                debug=engine.DEBUG,
                prefix=repository_structure['release'],
                origin=mock.ANY,
                canon=mock.ANY,
                master=mock.ANY,
                develop=mock.ANY,
                release=mock.ANY,
                hotfix=mock.ANY,
                repo=mock.ANY,
                gh=None,
                offline=True
            ),
        ])

        hotfix_manager.assert_has_calls([
            mock.call(
                debug=engine.DEBUG,
                prefix=repository_structure['hotfix'],
                origin=mock.ANY,
                canon=mock.ANY,
                master=mock.ANY,
                develop=mock.ANY,
                release=mock.ANY,
                hotfix=mock.ANY,
                repo=mock.ANY,
                gh=None,
                offline=True
            ),
        ])

        pull_manager.assert_has_calls([
            mock.call(
                debug=engine.DEBUG,
                prefix=repository_structure['name'],
                origin=mock.ANY,
                canon=mock.ANY,
                master=mock.ANY,
                develop=mock.ANY,
                release=mock.ANY,
                hotfix=mock.ANY,
                repo=mock.ANY,
                gh=None,
                offline=True
            ),
        ])

        return engine


class OnlineTestCase(object):
    @pytest.fixture
    def engine(self, git, repository_structure, configurator, feature_manager, release_manager, hotfix_manager, pull_manager, github):
        with mock.patch('flowhub.engine.getpass'):
            engine = Engine(init=True, input_func=lambda s: "")

        engine.setup_repository_structure(
            **repository_structure
        )

        # setup the configurator mock
        for key in ["name", "origin", "canon", "master", "develop"]:
            setattr(
                configurator().flowhub.structure,
                key,
                repository_structure[key]
            )
        for key in ["feature", "release", "hotfix"]:
            setattr(
                configurator().flowhub.prefix,
                key,
                repository_structure[key]
            )

        engine = Engine()
        feature_manager.assert_has_calls([
            mock.call(
                debug=engine.DEBUG,
                prefix=repository_structure['feature'],
                origin=mock.ANY,
                canon=mock.ANY,
                master=mock.ANY,
                develop=mock.ANY,
                release=mock.ANY,
                hotfix=mock.ANY,
                repo=mock.ANY,
                gh=github(),
                offline=False
            ),
        ])

        release_manager.assert_has_calls([
            mock.call(
                debug=engine.DEBUG,
                prefix=repository_structure['release'],
                origin=mock.ANY,
                canon=mock.ANY,
                master=mock.ANY,
                develop=mock.ANY,
                release=mock.ANY,
                hotfix=mock.ANY,
                repo=mock.ANY,
                gh=github(),
                offline=False
            ),
        ])

        hotfix_manager.assert_has_calls([
            mock.call(
                debug=engine.DEBUG,
                prefix=repository_structure['hotfix'],
                origin=mock.ANY,
                canon=mock.ANY,
                master=mock.ANY,
                develop=mock.ANY,
                release=mock.ANY,
                hotfix=mock.ANY,
                repo=mock.ANY,
                gh=github(),
                offline=False
            ),
        ])

        pull_manager.assert_has_calls([
            mock.call(
                debug=engine.DEBUG,
                prefix=repository_structure['name'],
                origin=mock.ANY,
                canon=mock.ANY,
                master=mock.ANY,
                develop=mock.ANY,
                release=mock.ANY,
                hotfix=mock.ANY,
                repo=mock.ANY,
                gh=github(),
                offline=False
            ),
        ])

        return engine


class OfflineFeatureTestCase(EngineTestCase, OfflineTestCase):

    def test_create_requires_arguments(self, engine):
        assert not engine.create_feature()

    def test_create(self, id_generator, engine, feature_manager):
        name = id_generator()
        assert engine.create_feature(name)

        feature_manager.assert_has_calls([
            mock.call().start(name, True, mock.ANY),
        ])

    def test_create_with_tracking(self, id_generator, engine, feature_manager):
        name = id_generator()

        assert engine.create_feature(name, False)

        feature_manager.assert_has_calls([
            mock.call().start(name, False, mock.ANY),
        ])

    def test_work_all_defaults(self, engine):
        assert not engine.work_feature()

    def test_work_single_branch(self, id_generator, feature_manager, engine):
        name = id_generator()
        branch = mock.MagicMock()
        feature_manager.return_value.fuzzy_get.return_value = [branch]

        engine.work_feature(name)

        feature_manager.assert_has_calls([
            mock.call().fuzzy_get(name),
        ])
        branch.assert_has_calls([
            mock.call.checkout(),
        ])

    def test_work_multiple_branches(self, id_generator, feature_manager, engine):
        name = id_generator()
        branch = mock.MagicMock()
        feature_manager.return_value.fuzzy_get.return_value = [branch, branch]

        engine.work_feature(name)

        feature_manager.assert_has_calls([
            mock.call().fuzzy_get(name),
        ])
        assert branch.call_count == 0

    def test_accept_all_defaults(self, engine):
        assert not engine.accept_feature()

    def test_accept(self, id_generator, engine, feature_manager, git):
        name = id_generator()
        return_branch = mock.MagicMock()
        git().head.reference = return_branch

        assert engine.accept_feature(name)

        feature_manager.assert_has_calls([
            mock.call().accept(
                name,
                summary=mock.ANY,
                with_delete=True,
            ),
        ])

        return_branch.assert_has_calls([
            mock.call.checkout(),
        ])

    def test_accept_while_on_branch(self, id_generator, engine, feature_manager, git, repository_structure):
        name = id_generator()
        git().head.reference.name = repository_structure['feature'] + name
        return_branch = engine.develop

        assert engine.accept_feature()

        feature_manager.assert_has_calls([
            mock.call().accept(name, summary=mock.ANY, with_delete=True),
        ])

        return_branch.assert_has_calls([
            mock.call.checkout(),
        ])

    def test_abandon_all_defaults(self, engine):
        assert not engine.abandon_feature()

    def test_abandon(self, id_generator, engine, feature_manager, git):
        name = id_generator()
        return_branch = mock.MagicMock()
        git().head.reference = return_branch

        assert engine.abandon_feature(name)

        return_branch.assert_has_calls([
            mock.call.checkout(),
        ])

        feature_manager.assert_has_calls([
            mock.call().abandon(name, summary=mock.ANY),
        ])

    def test_abandon_while_on_branch(self, id_generator, engine, feature_manager, git, repository_structure):
        name = id_generator()
        git().head.reference.name = repository_structure['feature'] + name
        return_branch = engine.develop

        assert engine.abandon_feature()

        return_branch.assert_has_calls([
            mock.call.checkout(),
        ])

        feature_manager.assert_has_calls([
            mock.call().abandon(name, summary=mock.ANY),
        ])

    def test_publish_all_defaults(self, engine):
        assert not engine.publish_feature()

    def test_publish(self, engine, id_generator):
        name = id_generator()

        assert not engine.publish_feature(name)


class OnlineFeatureTestCase(EngineTestCase, OnlineTestCase):

    def test_publish(self, id_generator, feature_manager, engine):
        name = id_generator()
        b = mock.MagicMock()
        feature_manager.return_value.publish.return_value = b

        assert engine.publish_feature(name)

        feature_manager.assert_has_calls([
            mock.call().publish(name, mock.ANY),
        ])


class OfflineReleaseTestCase(EngineTestCase, OfflineTestCase):

    def test_start_all_defaults(self, engine):
        assert not engine.start_release()

    def test_start(self, id_generator, release_manager, engine):
        name = id_generator()
        new_branch = mock.MagicMock()
        release_manager.return_value.start.return_value = new_branch
        assert engine.start_release(name)

        release_manager.assert_has_calls([
            mock.call().start(name, mock.ANY),
        ])

        new_branch.assert_has_calls([
            mock.call.checkout(),
        ])

    def test_start_with_existing_release(self, id_generator, git, engine, release_manager):
        name = id_generator()

        release_mock = mock.MagicMock()
        release_mock.name.startswith.return_value = True
        git().branches = [release_mock]

        assert not engine.start_release(name)

        assert release_manager.return_value.call_count == 0

    def test_publish_all_defaults(self, engine):
        assert not engine.publish_release()

    def test_publish_with_name(self, id_generator, engine, release_manager):
        name = id_generator()

        assert engine.publish_release(name)

        release_manager.assert_has_calls([
            mock.call().publish(name, True, None, mock.ANY)
        ])

    def test_publish_on_release_branch(self, engine, git, id_generator, repository_structure):
        return_branch = engine.develop
        git().head.reference.name = repository_structure['release'] + id_generator()

        assert engine.publish_release()

        return_branch.assert_has_calls([
            mock.call.checkout(),
        ])

    def test_publish_with_name_tag_info_and_no_delete(self, id_generator, engine, release_manager):
        name = id_generator()
        tag_label = id_generator()
        tag_message = id_generator()

        assert engine.publish_release(
            name,
            with_delete=False,
            tag_info=TagInfo(tag_label, tag_message),
        )

        release_manager.assert_has_calls([
            mock.call().publish(name, False, TagInfo(tag_label, tag_message), mock.ANY)
        ])

    def test_contribute(self, engine):
        assert not engine.contribute_release()


class OnlineReleaseTestCase(EngineTestCase, OnlineTestCase):

    def test_contribute(self, git, engine, release_manager):
        release_mock = mock.MagicMock()
        release_mock.name.startswith.return_value = True
        release_mock.commit = True

        git().branches = [release_mock]

        git().head.reference.object.iter_parents.return_value = [True]

        assert engine.contribute_release()

        release_manager.assert_has_calls([
            mock.call().contribute(git().head.reference, mock.ANY),
        ])


class OfflineHotfixTestCase(EngineTestCase, OfflineTestCase):

    def test_start_all_defaults(self, engine):
        assert not engine.start_hotfix()

    def test_start(self, engine, id_generator, hotfix_manager):
        name = id_generator()
        return_branch = hotfix_manager.return_value.start.return_value

        assert engine.start_hotfix(name)

        hotfix_manager.assert_has_calls([
            mock.call().start(name, None, mock.ANY),
        ])

        return_branch.assert_has_calls([
            mock.call.checkout(),
        ])

    def test_start_with_issues(self, id_generator, hotfix_manager, engine):
        name = id_generator()
        issues = mock.MagicMock()
        return_branch = hotfix_manager.return_value.start.return_value

        assert engine.start_hotfix(name, issues)

        hotfix_manager.assert_has_calls([
            mock.call().start(name, issues, mock.ANY),
        ])

        return_branch.assert_has_calls([
            mock.call.checkout(),
        ])

    def test_start_with_existing_hotfix(self, id_generator, git, engine, hotfix_manager):
        name = id_generator()

        hotfix_mock = mock.MagicMock()
        hotfix_mock.name.startswith.return_value = True
        git().branches = [hotfix_mock]

        assert not engine.start_hotfix(name)

        assert hotfix_manager.return_value.call_count == 0

    def test_publish_all_defaults(self, engine):
        assert not engine.publish_hotfix()

    def test_publish_not_on_hotfix_branch(self, id_generator, git, engine, hotfix_manager):
        name = id_generator()

        return_branch = mock.MagicMock()
        git().head.reference = return_branch

        assert engine.publish_hotfix(name)

        hotfix_manager.assert_has_calls([
            mock.call().publish(name, None, True, mock.ANY),
        ])

        return_branch.assert_has_calls([
            mock.call.checkout(),
        ])

    def test_publish_on_hotfix_branch(self, engine, git, id_generator, repository_structure):
        return_branch = engine.develop
        git().head.reference.name = repository_structure['hotfix'] + id_generator()

        assert engine.publish_hotfix()

        return_branch.assert_has_calls([
            mock.call.checkout(),
        ])

    def test_contribute(self, engine):
        assert not engine.contribute_hotfix()


class OnlineHotfixTestCase(EngineTestCase, OnlineTestCase):

    def test_contribute(self, git, engine, release_manager):
        hotfix_mock = mock.MagicMock()
        hotfix_mock.name.startswith.return_value = True
        hotfix_mock.commit = True

        git().branches = [hotfix_mock]

        git().head.reference.object.iter_parents.return_value = [True]

        assert engine.contribute_hotfix()

        release_manager.assert_has_calls([
            mock.call().contribute(git().head.reference, mock.ANY),
        ])

    def test_contribute_on_wrong_branch_by_existance(self, git, engine):
        git().branches = []
        assert not engine.contribute_hotfix()

    def test_contribute_on_wrong_branch_by_commit(self, git, engine):
        hotfix_mock = mock.MagicMock()
        hotfix_mock.name.startswith.return_value = True

        git().branches = [hotfix_mock]

        # ensure that the "commit" isn't in the iter_parents
        hotfix_mock.commit = False
        git().head.reference.object.iter_parents.return_value = [True]

        assert not engine.contribute_hotfix()
