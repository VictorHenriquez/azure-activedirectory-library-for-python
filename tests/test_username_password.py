﻿#------------------------------------------------------------------------------
#
# Copyright (c) Microsoft Corporation. 
# All rights reserved.
# 
# This code is licensed under the MIT License.
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files(the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and / or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions :
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
#------------------------------------------------------------------------------

import sys
import requests
import httpretty

try:
    import unittest2 as unittest
except ImportError:
    import unittest

try:
    from unittest import mock
except ImportError:
    import mock

from tests import util
from tests.util import parameters as cp

import adal
from adal.authentication_context import AuthenticationContext
from adal.mex import Mex
from adal.token_request import TokenRequest
from adal.oauth2_client import OAuth2Client
from adal.user_realm import UserRealm
from adal.wstrust_response import WSTrustResponse
from adal.wstrust_request import WSTrustRequest
from adal import log
from adal.authority import Authority
from adal.constants import AADConstants

try:
    from urllib.parse import urlparse, urlencode
except ImportError:
    from urllib import urlencode
    from urlparse import urlparse

try:
    from tests.config import ACQUIRE_TOKEN_WITH_USERNAME_PASSWORD as user_pass_params
    from tests.config import ACQUIRE_TOKEN_WITH_CLIENT_CREDENTIALS as client_cred_params
except:
    raise Exception("Author a config.py with values for the tests. See config_sample.py for details.")

class TestUsernamePassword(unittest.TestCase):

    def setUp(self):
        util.reset_logging()
        util.clear_static_cache()

    def tearDown(self):
        util.reset_logging()
        util.clear_static_cache()

    def setup_expected_oauth_assertion_request(self, response):
        assertion = open(cp['AssertionFile']).read()

        queryParameters = {}
        queryParameters['grant_type'] = 'urn:ietf:params:oauth:grant-type:saml1_1-bearer'
        queryParameters['client_id'] = response['clientId']
        queryParameters['resource'] = response['resource']
        queryParameters['assertion'] = assertion
        queryParameters['scope'] = 'openid'

        return util.setup_expected_oauth_response(queryParameters, cp['tokenUrlPath'], 200, response['wireResponse'], cp['authority'] + '/' + cp['tenant'])

    def setup_expected_username_password_request_response(self, httpCode, returnDoc, authorityEndpoint):
        queryParameters = {}
        queryParameters['grant_type'] = 'password'
        queryParameters['client_id'] = client_cred_params['clientId']
        queryParameters['resource'] = cp['resource']
        queryParameters['username'] = user_pass_params['username']
        queryParameters['password'] = user_pass_params['password']
        queryParameters['scope'] = 'openid'

        query = urlencode(queryParameters)

        url = '{}{}'.format(authorityEndpoint, cp['tokenPath'])
        #'https://login.windows.net/rrandallaad1.onmicrosoft.com/oauth2/token?slice=testslice&api-version=1.0'
        httpretty.register_uri(httpretty.POST, url, returnDoc, status = httpCode, content_type = 'text/json')

    @unittest.skip('https://github.com/AzureAD/azure-activedirectory-library-for-python-priv/issues/21')
    @httpretty.activate
    def test_managed_happy_path(self):
        util.setup_expected_user_realm_response_common(False)
        response = util.create_response()

        authorityUrl = response['authority'] + '/' + cp['tenant']
        upRequest = self.setup_expected_username_password_request_response(200, response['wireResponse'], authorityUrl)

        context = adal.AuthenticationContext(authorityUrl)
        token_response = context.acquire_token_with_username_password(response['resource'], user_pass_params['username'], user_pass_params['password'], client_cred_params['clientId'])
        self.assertTrue(util.isMatchTokenResponse(response['cachedResponse'], token_response), 'Response did not match expected: ' + JSON.stringify(token_response))


    # Since this test is the most code intensive it will make a good test case for
    # correlation id.
    @unittest.skip('https://github.com/AzureAD/azure-activedirectory-library-for-python-priv/issues/21')
    def test_federated_happy_path_and_correlation_id(self):
        correlationId = '12300002-0000-0000-c000-000000000000'
        util.set_correlation_id(correlationId)

        util.setup_expected_user_realm_response_common(True)
        util.setup_expected_mex_wstrust_request_common()

        response = util.create_response()
        assertion = self.setup_expected_oauth_assertion_request(response)

        logFunctionCalled = False
        def testCorrelationIdLog(level, message):
            logFunctionCalled = True
            self.assertIsNotNone(message)


        logOptions = {
            'level' : 3,
            'log' : testCorrelationIdLog
        }
        oldOptions = log.get_logging_options()
        log.set_logging_options(logOptions)

        authorityUrl = response['authority'] + '/' + cp['tenant']

        context = adal.AuthenticationContext(authorityUrl)
        token_response = context.acquire_token_with_username_password(response['resource'], user_pass_params['username'], user_pass_params['password'], client_cred_params['clientId'])
        self.assertTrue(util.isMatchTokenResponse(response['cachedResponse'], token_response), 'Response did not match expected: ' + JSON.stringify(token_response))
        log.set_logging_options(oldOptions)
        util.set_correlation_id()

        self.assertTrue(util.isMatchTokenResponse(response['cachedResponse'], token_response), 'The response did not match what was expected')
        self.assertTrue(logFunctionCalled, 'Logging was turned on but no messages were recieved.')

    @unittest.skip('https://github.com/AzureAD/azure-activedirectory-library-for-python-priv/issues/21')
    @httpretty.activate
    def test_invalid_id_token(self):
        ''' TODO: Test Failing as of 2015/06/03 and needs to be completed. '''
        util.setup_expected_user_realm_response_common(False)
        response = util.create_response()
        wireResponse = response['wireResponse']

        response_options = { 'noIdToken' : True }
        #response = util.create_response(response_options)

        # break the id token
        #idToken = wireResponse['id_token']
        #idToken = idToken.replace('.', ' ')
        #wireResponse['id_token'] = idToken
        authorityUrl = response['authority'] + '/' + cp['tenant']
        upRequest = self.setup_expected_username_password_request_response(200, wireResponse, authorityUrl)

        context = adal.AuthenticationContext(authorityUrl)
        token_response = context.acquire_token_with_username_password(response['resource'], user_pass_params['username'], user_pass_params['password'], client_cred_params['clientId'])
        self.assertTrue(util.isMatchTokenResponse(response['cachedResponse'], token_response), 'Response did not match expected: ' + JSON.stringify(token_response))

    def create_mex_stub(self, usernamePasswordUrl, err=None):
        mex = Mex(cp['callContext'], '')

        mex.discover = mock.MagicMock()

        mex._usernamePasswordUrl = usernamePasswordUrl
        mex.username_password_url = usernamePasswordUrl
        return mex

    def create_user_realm_stub(self, protocol, accountType, mexUrl, wstrustUrl, err=None):
        userRealm = UserRealm(cp['callContext'], '', '')

        userRealm.discover = mock.MagicMock()

        userRealm._federationProtocol = protocol
        userRealm._accountType = accountType
        userRealm._federationMetadataUrl = mexUrl
        userRealm.federation_metadata_url = mexUrl
        userRealm._federationActiveAuthUrl = wstrustUrl
        userRealm.federation_active_auth_url = wstrustUrl
        userRealm.account_type = accountType
        return userRealm

    def create_wstrust_request_stub(self, err, tokenType, noToken=None):
        wstrust_response = WSTrustResponse(cp['callContext'],'')
        wstrust_response.error_code = err
        wstrust_response.parse = mock.MagicMock()
        if not noToken:
            wstrust_response.token = 'This is a stubbed token'
            wstrust_response._tokenType = tokenType
            wstrust_response.token_type = tokenType

        wstrust_request = WSTrustRequest(cp['callContext'], '', '')

        def side_effect (username, password):
            if err:
                raise AdalError("Throwing error from Unit test")
            return wstrust_response
        wstrust_request.acquire_token = mock.MagicMock(side_effect=side_effect)

        return wstrust_request

    def create_authentication_context_stub(self, authority):
        context = AuthenticationContext(authority, False)
        context.authority._tokenEndpoint = authority + cp['tokenPath']
        return context

    def create_oauth2_client_stub(self, authority, token_response, err):
        authorityObject = Authority(authority, False)
        authorityObject.token_endpoint = AADConstants.TOKEN_ENDPOINT_PATH
        authorityObject.device_code_endpoint = AADConstants.DEVICE_ENDPOINT_PATH
        client = OAuth2Client(cp['callContext'], authorityObject)

        def side_effect (oauth):
            return token_response
        client.get_token = mock.MagicMock(side_effect=side_effect)

        return client

    def stub_out_token_request_dependencies(self, tokenRequest, userRealm, mex, wstrustRequest=None, oauthClient=None):
        tokenRequest._create_user_realm_request = mock.MagicMock(return_value=userRealm)
        tokenRequest._create_mex = mock.MagicMock(return_value=mex)
        tokenRequest._create_wstrust_request = mock.MagicMock(return_value=wstrustRequest)
        tokenRequest._create_oauth2client = mock.MagicMock(return_value=oauthClient)
        tokenRequest._create_oauth2_client = mock.MagicMock(return_value=oauthClient)

    def test_federated_failed_mex(self):
        context = self.create_authentication_context_stub(cp['authorityTenant'])
        mex = self.create_mex_stub(cp['adfsWsTrust'], Exception('mex failed'))
        userRealm = self.create_user_realm_stub('wstrust', 'federated', cp['adfsMex'], cp['adfsWsTrust'])
        wstrustRequest = self.create_wstrust_request_stub(None, 'urn:oasis:names:tc:SAML:1.0:assertion')

        response = util.create_response()
        oauthClient = self.create_oauth2_client_stub(cp['authority'], response['cachedResponse'], None)

        tokenRequest = TokenRequest(cp['callContext'], context, response['clientId'], response['resource'])
        self.stub_out_token_request_dependencies(tokenRequest, userRealm, mex, wstrustRequest, oauthClient)

        receivedException = True
        try:
            token_response = tokenRequest.get_token_with_username_password(user_pass_params['username'], user_pass_params['password'])
        except Exception as exp:
            receivedException = True
            pass
        finally:
            if not receivedException:
                self.assertTrue(util.is_match_token_response(response['cachedResponse'], token_response), 'The response did not match what was expected')

    def test_federated_user_realm_returns_no_mex_endpoint(self):
        context = self.create_authentication_context_stub(cp['authority'])
        mex = self.create_mex_stub(cp['adfsWsTrust'])
        userRealm = self.create_user_realm_stub('wstrust', 'federated', None, cp['adfsWsTrust'])
        wstrustRequest = self.create_wstrust_request_stub(None, 'urn:oasis:names:tc:SAML:1.0:assertion')

        response = util.create_response()
        oauthClient = self.create_oauth2_client_stub(cp['authority'], response['decodedResponse'], None)

        #util.turnOnLogging()
        tokenRequest = TokenRequest(cp['callContext'], context, response['clientId'], response['resource'])
        self.stub_out_token_request_dependencies(tokenRequest, userRealm, mex, wstrustRequest, oauthClient)

        receivedException = False
        try:
            token_response = tokenRequest.get_token_with_username_password(user_pass_params['username'], user_pass_params['password'])
        except Exception as exp:
            receivedException = True
            pass
        finally:
            if not receivedException:
                self.assertTrue(util.is_match_token_response(response['cachedResponse'], token_response), 'The response did not match what was expected')

    def test_user_realm_returns_unknown_account_type(self):
        context = self.create_authentication_context_stub(cp['authorityTenant'])
        mex = self.create_mex_stub(cp['adfsWsTrust'])
        userRealm = self.create_user_realm_stub('wstrust', 'unknown', cp['adfsMex'], cp['adfsWsTrust'])

        tokenRequest = TokenRequest(cp['callContext'], context, client_cred_params['clientId'], cp['resource'])
        self.stub_out_token_request_dependencies(tokenRequest, userRealm, mex)

        raisedException = False
        try:
            tokenRequest.get_token_with_username_password(user_pass_params['username'], user_pass_params['password'])
        except Exception as err:
            self.assertTrue(err, 'Did not receive expected err.')
            self.assertTrue('unknown AccountType' in  err.args[0], 'Did not receive expected error message.')
            raisedException = True
            pass
        finally:
            self.assertTrue(raisedException, 'Exception not raised, when it should have been')

    def test_federated_saml2(self):
        context = self.create_authentication_context_stub(cp['authorityTenant'])
        mex = self.create_mex_stub(cp['adfsWsTrust'])
        userRealm = self.create_user_realm_stub('wstrust', 'federated', cp['adfsMex'], cp['adfsWsTrust'])
        wstrustRequest = self.create_wstrust_request_stub(None, 'urn:oasis:names:tc:SAML:2.0:assertion')

        response = util.create_response()
        oauthClient = self.create_oauth2_client_stub(cp['authority'], response['cachedResponse'], None)

        #util.turnOnLogging()
        tokenRequest = TokenRequest(cp['callContext'], context, response['clientId'], response['resource'])
        self.stub_out_token_request_dependencies(tokenRequest, userRealm, mex, wstrustRequest, oauthClient)

        try:
            token_response = tokenRequest.get_token_with_username_password(user_pass_params['username'], user_pass_params['password'])
            self.assertTrue(util.is_match_token_response(response['cachedResponse'], token_response), 'The response did not match what was expected')
        except Exception as err:
            self.assertTrue(False)
            pass

    @unittest.skip('https://github.com/AzureAD/azure-activedirectory-library-for-python-priv/issues/21')
    def test_federated_unknown_token_type(self):
        ''' TODO: Test Failing as of 2015/06/03 and needs to be completed. '''
        context = self.create_authentication_context_stub(cp['authorityTenant'])
        mex = self.create_mex_stub(cp['adfsWsTrust'])
        userRealm = self.create_user_realm_stub('wstrust', 'federated', cp['adfsMex'], cp['adfsWsTrust'])
        wstrustRequest = self.create_wstrust_request_stub(None, 'urn:oasis:names:tc:SAML:100.0:assertion')

        response = util.create_response()
        oauthClient = self.create_oauth2_client_stub(cp['authority'], response['decodedResponse'], None)

        #util.turnOnLogging()
        tokenRequest = TokenRequest(cp['callContext'], context, response['clientId'], response['resource'])
        self.stub_out_token_request_dependencies(tokenRequest, userRealm, mex, wstrustRequest, oauthClient)

        try:
            tokenRequest.get_token_with_username_password(user_pass_params['username'], user_pass_params['password'])
        except Exception as err:
            receivedException = True
            self.assertTrue('tokenType' in  err.args[0], "Error message did not contain 'token type'. message:{}".format(err.args[0]))
            pass
        finally:
            self.assertTrue(receivedException, 'Did not receive expected error')

    def test_federated_failed_wstrust(self):
        context = self.create_authentication_context_stub(cp['authorityTenant'])
        mex = self.create_mex_stub(cp['adfsWsTrust'])
        userRealm = self.create_user_realm_stub('wstrust', 'federated', None, cp['adfsWsTrust'])
        wstrustRequest = self.create_wstrust_request_stub(Exception('Network not available'), 'urn:oasis:names:tc:SAML:1.0:assertion')

        response = util.create_response()
        oauthClient = self.create_oauth2_client_stub(cp['authority'], response['cachedResponse'], None)

        #util.turnOnLogging()
        tokenRequest = TokenRequest(cp['callContext'], context, response['clientId'], response['resource'])
        self.stub_out_token_request_dependencies(tokenRequest, userRealm, mex, wstrustRequest, oauthClient)

        receivedException = False
        try:
            tokenRequest.get_token_with_username_password(user_pass_params['username'], user_pass_params['password'])
        except Exception as exp:
            receivedException = True
            pass
        finally:
            self.assertTrue(receivedException, 'Did not receive expected error')

    def test_federated_wstrust_unparseable(self):
        context = self.create_authentication_context_stub(cp['authorityTenant'])
        mex = self.create_mex_stub(cp['adfsWsTrust'])
        userRealm = self.create_user_realm_stub('wstrust', 'federated', None, cp['adfsWsTrust'])
        wstrustRequest = self.create_wstrust_request_stub(None, 'urn:oasis:names:tc:SAML:2.0:assertion', True)

        response = util.create_response()
        oauthClient = self.create_oauth2_client_stub(cp['authority'], response['decodedResponse'], None)

        #util.turnOnLogging()
        tokenRequest = TokenRequest(cp['callContext'], context, response['clientId'], response['resource'])
        self.stub_out_token_request_dependencies(tokenRequest, userRealm, mex, wstrustRequest, oauthClient)

        try:
            tokenRequest.get_token_with_username_password(user_pass_params['username'], user_pass_params['password'])
        except Exception as exp:
            receivedException = True
            pass
        finally:
            self.assertTrue(receivedException, 'Did not receive expected error')

    def test_federated_wstrust_unknown_token_type(self):
        context = self.create_authentication_context_stub(cp['authorityTenant'])
        mex = self.create_mex_stub(cp['adfsWsTrust'])
        userRealm = self.create_user_realm_stub('wstrust', 'federated', None, cp['adfsWsTrust'])
        wstrustRequest = self.create_wstrust_request_stub(None, 'urn:oasis:names:tc:SAML:100.0:assertion', True)

        response = util.create_response()
        oauthClient = self.create_oauth2_client_stub(cp['authority'], response['decodedResponse'], None)

        #util.turnOnLogging()
        tokenRequest = TokenRequest(cp['callContext'], context, response['clientId'], response['resource'])
        self.stub_out_token_request_dependencies(tokenRequest, userRealm, mex, wstrustRequest, oauthClient)

        try:
            tokenRequest.get_token_with_username_password(user_pass_params['username'], user_pass_params['password'])
        except Exception as exp:
            receivedException = True
            pass
        finally:
            self.assertTrue(receivedException, 'Did not receive expected error')

    def test_jwt_cracking(self):
        testData = [
          [
            'eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0.eyJhdWQiOiJlOTU4YzA5YS1hYzM3LTQ5MDAtYjRkNy1mYjNlZWFmNzMzOGQiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9jY2ViYTE0Yy02YTAwLTQ5YWMtYjgwNi04NGRlNTJiZjFkNDIvIiwiaWF0IjoxMzkxNjQ1NDU4LCJuYmYiOjEzOTE2NDU0NTgsImV4cCI6MTM5MTY0OTM1OCwidmVyIjoiMS4wIiwidGlkIjoiY2NlYmExNGMtNmEwMC00OWFjLWI4MDYtODRkZTUyYmYxZDQyIiwib2lkIjoiYTQ0MzIwNGEtYWJjOS00Y2I4LWFkYzEtYzBkZmMxMjMwMGFhIiwidXBuIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInVuaXF1ZV9uYW1lIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInN1YiI6IjRnVHY0RXRvWVctRFRvdzBiRG5KZDFBQTRzZkNoQmJqZXJtcXQ2UV9aYTQiLCJmYW1pbHlfbmFtZSI6IlJhbmRhbGwiLCJnaXZlbl9uYW1lIjoiUmljaCJ9.',
            {
              'header' : 'eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0',
              'JWSPayload' : 'eyJhdWQiOiJlOTU4YzA5YS1hYzM3LTQ5MDAtYjRkNy1mYjNlZWFmNzMzOGQiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9jY2ViYTE0Yy02YTAwLTQ5YWMtYjgwNi04NGRlNTJiZjFkNDIvIiwiaWF0IjoxMzkxNjQ1NDU4LCJuYmYiOjEzOTE2NDU0NTgsImV4cCI6MTM5MTY0OTM1OCwidmVyIjoiMS4wIiwidGlkIjoiY2NlYmExNGMtNmEwMC00OWFjLWI4MDYtODRkZTUyYmYxZDQyIiwib2lkIjoiYTQ0MzIwNGEtYWJjOS00Y2I4LWFkYzEtYzBkZmMxMjMwMGFhIiwidXBuIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInVuaXF1ZV9uYW1lIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInN1YiI6IjRnVHY0RXRvWVctRFRvdzBiRG5KZDFBQTRzZkNoQmJqZXJtcXQ2UV9aYTQiLCJmYW1pbHlfbmFtZSI6IlJhbmRhbGwiLCJnaXZlbl9uYW1lIjoiUmljaCJ9',
              'JWSSig' : ''
            }
          ],
          # remove header
          [
            '.eyJhdWQiOiJlOTU4YzA5YS1hYzM3LTQ5MDAtYjRkNy1mYjNlZWFmNzMzOGQiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9jY2ViYTE0Yy02YTAwLTQ5YWMtYjgwNi04NGRlNTJiZjFkNDIvIiwiaWF0IjoxMzkxNjQ1NDU4LCJuYmYiOjEzOTE2NDU0NTgsImV4cCI6MTM5MTY0OTM1OCwidmVyIjoiMS4wIiwidGlkIjoiY2NlYmExNGMtNmEwMC00OWFjLWI4MDYtODRkZTUyYmYxZDQyIiwib2lkIjoiYTQ0MzIwNGEtYWJjOS00Y2I4LWFkYzEtYzBkZmMxMjMwMGFhIiwidXBuIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInVuaXF1ZV9uYW1lIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInN1YiI6IjRnVHY0RXRvWVctRFRvdzBiRG5KZDFBQTRzZkNoQmJqZXJtcXQ2UV9aYTQiLCJmYW1pbHlfbmFtZSI6IlJhbmRhbGwiLCJnaXZlbl9uYW1lIjoiUmljaCJ9.',
            {
              'header' : '',
              'JWSPayload' : 'eyJhdWQiOiJlOTU4YzA5YS1hYzM3LTQ5MDAtYjRkNy1mYjNlZWFmNzMzOGQiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9jY2ViYTE0Yy02YTAwLTQ5YWMtYjgwNi04NGRlNTJiZjFkNDIvIiwiaWF0IjoxMzkxNjQ1NDU4LCJuYmYiOjEzOTE2NDU0NTgsImV4cCI6MTM5MTY0OTM1OCwidmVyIjoiMS4wIiwidGlkIjoiY2NlYmExNGMtNmEwMC00OWFjLWI4MDYtODRkZTUyYmYxZDQyIiwib2lkIjoiYTQ0MzIwNGEtYWJjOS00Y2I4LWFkYzEtYzBkZmMxMjMwMGFhIiwidXBuIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInVuaXF1ZV9uYW1lIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInN1YiI6IjRnVHY0RXRvWVctRFRvdzBiRG5KZDFBQTRzZkNoQmJqZXJtcXQ2UV9aYTQiLCJmYW1pbHlfbmFtZSI6IlJhbmRhbGwiLCJnaXZlbl9uYW1lIjoiUmljaCJ9',
              'JWSSig' : ''
            }
          ],
          # Add JWSSig
          [
            'eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0.eyJhdWQiOiJlOTU4YzA5YS1hYzM3LTQ5MDAtYjRkNy1mYjNlZWFmNzMzOGQiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9jY2ViYTE0Yy02YTAwLTQ5YWMtYjgwNi04NGRlNTJiZjFkNDIvIiwiaWF0IjoxMzkxNjQ1NDU4LCJuYmYiOjEzOTE2NDU0NTgsImV4cCI6MTM5MTY0OTM1OCwidmVyIjoiMS4wIiwidGlkIjoiY2NlYmExNGMtNmEwMC00OWFjLWI4MDYtODRkZTUyYmYxZDQyIiwib2lkIjoiYTQ0MzIwNGEtYWJjOS00Y2I4LWFkYzEtYzBkZmMxMjMwMGFhIiwidXBuIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInVuaXF1ZV9uYW1lIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInN1YiI6IjRnVHY0RXRvWVctRFRvdzBiRG5KZDFBQTRzZkNoQmJqZXJtcXQ2UV9aYTQiLCJmYW1pbHlfbmFtZSI6IlJhbmRhbGwiLCJnaXZlbl9uYW1lIjoiUmljaCJ9.foobar',
            {
              'header' : 'eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0',
              'JWSPayload' : 'eyJhdWQiOiJlOTU4YzA5YS1hYzM3LTQ5MDAtYjRkNy1mYjNlZWFmNzMzOGQiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9jY2ViYTE0Yy02YTAwLTQ5YWMtYjgwNi04NGRlNTJiZjFkNDIvIiwiaWF0IjoxMzkxNjQ1NDU4LCJuYmYiOjEzOTE2NDU0NTgsImV4cCI6MTM5MTY0OTM1OCwidmVyIjoiMS4wIiwidGlkIjoiY2NlYmExNGMtNmEwMC00OWFjLWI4MDYtODRkZTUyYmYxZDQyIiwib2lkIjoiYTQ0MzIwNGEtYWJjOS00Y2I4LWFkYzEtYzBkZmMxMjMwMGFhIiwidXBuIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInVuaXF1ZV9uYW1lIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInN1YiI6IjRnVHY0RXRvWVctRFRvdzBiRG5KZDFBQTRzZkNoQmJqZXJtcXQ2UV9aYTQiLCJmYW1pbHlfbmFtZSI6IlJhbmRhbGwiLCJnaXZlbl9uYW1lIjoiUmljaCJ9',
              'JWSSig' : 'foobar'
            }
          ],
          # Remove JWS payload
          [
            'eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0..',
            None
          ],
          # Remove JWS payload
          [
            'eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0..foobar',
            None
          ],
          # JWT payload is only a space.
          [
            'eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0. .foobar',
            None
          ],
          # Add space
          [
            'eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0.eyJhdWQiOiJlOTU4YzA5YS1hYzM3LTQ5MDAtYjRkNy1 mYjNlZWFmNzMzOGQiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9jY2ViYTE0Yy02YTAwLTQ5YWMtYjgwNi04NGRlNTJiZjFkNDIvIiwiaWF0IjoxMzkxNjQ1NDU4LCJuYmYiOjEzOTE2NDU0NTgsImV4cCI6MTM5MTY0OTM1OCwidmVyIjoiMS4wIiwidGlkIjoiY2NlYmExNGMtNmEwMC00OWFjLWI4MDYtODRkZTUyYmYxZDQyIiwib2lkIjoiYTQ0MzIwNGEtYWJjOS00Y2I4LWFkYzEtYzBkZmMxMjMwMGFhIiwidXBuIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInVuaXF1ZV9uYW1lIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInN1YiI6IjRnVHY0RXRvWVctRFRvdzBiRG5KZDFBQTRzZkNoQmJqZXJtcXQ2UV9aYTQiLCJmYW1pbHlfbmFtZSI6IlJhbmRhbGwiLCJnaXZlbl9uYW1lIjoiUmljaCJ9.',
            None
          ],
          # remove first period.
          [
            'eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0eyJhdWQiOiJlOTU4YzA5YS1hYzM3LTQ5MDAtYjRkNy1mYjNlZWFmNzMzOGQiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9jY2ViYTE0Yy02YTAwLTQ5YWMtYjgwNi04NGRlNTJiZjFkNDIvIiwiaWF0IjoxMzkxNjQ1NDU4LCJuYmYiOjEzOTE2NDU0NTgsImV4cCI6MTM5MTY0OTM1OCwidmVyIjoiMS4wIiwidGlkIjoiY2NlYmExNGMtNmEwMC00OWFjLWI4MDYtODRkZTUyYmYxZDQyIiwib2lkIjoiYTQ0MzIwNGEtYWJjOS00Y2I4LWFkYzEtYzBkZmMxMjMwMGFhIiwidXBuIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInVuaXF1ZV9uYW1lIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInN1YiI6IjRnVHY0RXRvWVctRFRvdzBiRG5KZDFBQTRzZkNoQmJqZXJtcXQ2UV9aYTQiLCJmYW1pbHlfbmFtZSI6IlJhbmRhbGwiLCJnaXZlbl9uYW1lIjoiUmljaCJ9.',
            None
          ],
          # remove second period.
          [
            'eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0.eyJhdWQiOiJlOTU4YzA5YS1hYzM3LTQ5MDAtYjRkNy1mYjNlZWFmNzMzOGQiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9jY2ViYTE0Yy02YTAwLTQ5YWMtYjgwNi04NGRlNTJiZjFkNDIvIiwiaWF0IjoxMzkxNjQ1NDU4LCJuYmYiOjEzOTE2NDU0NTgsImV4cCI6MTM5MTY0OTM1OCwidmVyIjoiMS4wIiwidGlkIjoiY2NlYmExNGMtNmEwMC00OWFjLWI4MDYtODRkZTUyYmYxZDQyIiwib2lkIjoiYTQ0MzIwNGEtYWJjOS00Y2I4LWFkYzEtYzBkZmMxMjMwMGFhIiwidXBuIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInVuaXF1ZV9uYW1lIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInN1YiI6IjRnVHY0RXRvWVctRFRvdzBiRG5KZDFBQTRzZkNoQmJqZXJtcXQ2UV9aYTQiLCJmYW1pbHlfbmFtZSI6IlJhbmRhbGwiLCJnaXZlbl9uYW1lIjoiUmljaCJ9',
            None
          ],
          # prefixed space
          [
            '  eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0.eyJhdWQiOiJlOTU4YzA5YS1hYzM3LTQ5MDAtYjRkNy1mYjNlZWFmNzMzOGQiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9jY2ViYTE0Yy02YTAwLTQ5YWMtYjgwNi04NGRlNTJiZjFkNDIvIiwiaWF0IjoxMzkxNjQ1NDU4LCJuYmYiOjEzOTE2NDU0NTgsImV4cCI6MTM5MTY0OTM1OCwidmVyIjoiMS4wIiwidGlkIjoiY2NlYmExNGMtNmEwMC00OWFjLWI4MDYtODRkZTUyYmYxZDQyIiwib2lkIjoiYTQ0MzIwNGEtYWJjOS00Y2I4LWFkYzEtYzBkZmMxMjMwMGFhIiwidXBuIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInVuaXF1ZV9uYW1lIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInN1YiI6IjRnVHY0RXRvWVctRFRvdzBiRG5KZDFBQTRzZkNoQmJqZXJtcXQ2UV9aYTQiLCJmYW1pbHlfbmFtZSI6IlJhbmRhbGwiLCJnaXZlbl9uYW1lIjoiUmljaCJ9.foobar',
            None
          ],
          # trailing space
          [
            'eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0.eyJhdWQiOiJlOTU4YzA5YS1hYzM3LTQ5MDAtYjRkNy1mYjNlZWFmNzMzOGQiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9jY2ViYTE0Yy02YTAwLTQ5YWMtYjgwNi04NGRlNTJiZjFkNDIvIiwiaWF0IjoxMzkxNjQ1NDU4LCJuYmYiOjEzOTE2NDU0NTgsImV4cCI6MTM5MTY0OTM1OCwidmVyIjoiMS4wIiwidGlkIjoiY2NlYmExNGMtNmEwMC00OWFjLWI4MDYtODRkZTUyYmYxZDQyIiwib2lkIjoiYTQ0MzIwNGEtYWJjOS00Y2I4LWFkYzEtYzBkZmMxMjMwMGFhIiwidXBuIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInVuaXF1ZV9uYW1lIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInN1YiI6IjRnVHY0RXRvWVctRFRvdzBiRG5KZDFBQTRzZkNoQmJqZXJtcXQ2UV9aYTQiLCJmYW1pbHlfbmFtZSI6IlJhbmRhbGwiLCJnaXZlbl9uYW1lIjoiUmljaCJ9.foobar  ',
            None
          ],
          # add section
          [
            'notsupposedtobehere.eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0.eyJhdWQiOiJlOTU4YzA5YS1hYzM3LTQ5MDAtYjRkNy1mYjNlZWFmNzMzOGQiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9jY2ViYTE0Yy02YTAwLTQ5YWMtYjgwNi04NGRlNTJiZjFkNDIvIiwiaWF0IjoxMzkxNjQ1NDU4LCJuYmYiOjEzOTE2NDU0NTgsImV4cCI6MTM5MTY0OTM1OCwidmVyIjoiMS4wIiwidGlkIjoiY2NlYmExNGMtNmEwMC00OWFjLWI4MDYtODRkZTUyYmYxZDQyIiwib2lkIjoiYTQ0MzIwNGEtYWJjOS00Y2I4LWFkYzEtYzBkZmMxMjMwMGFhIiwidXBuIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInVuaXF1ZV9uYW1lIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInN1YiI6IjRnVHY0RXRvWVctRFRvdzBiRG5KZDFBQTRzZkNoQmJqZXJtcXQ2UV9aYTQiLCJmYW1pbHlfbmFtZSI6IlJhbmRhbGwiLCJnaXZlbl9uYW1lIjoiUmljaCJ9.foobar',
            None
          ],
          # extra stuff at beginning seperated by space.
          [
            'stuff eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0.eyJhdWQiOiJlOTU4YzA5YS1hYzM3LTQ5MDAtYjRkNy1mYjNlZWFmNzMzOGQiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9jY2ViYTE0Yy02YTAwLTQ5YWMtYjgwNi04NGRlNTJiZjFkNDIvIiwiaWF0IjoxMzkxNjQ1NDU4LCJuYmYiOjEzOTE2NDU0NTgsImV4cCI6MTM5MTY0OTM1OCwidmVyIjoiMS4wIiwidGlkIjoiY2NlYmExNGMtNmEwMC00OWFjLWI4MDYtODRkZTUyYmYxZDQyIiwib2lkIjoiYTQ0MzIwNGEtYWJjOS00Y2I4LWFkYzEtYzBkZmMxMjMwMGFhIiwidXBuIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInVuaXF1ZV9uYW1lIjoicnJhbmRhbGxAcnJhbmRhbGxhYWQxLm9ubWljcm9zb2Z0LmNvbSIsInN1YiI6IjRnVHY0RXRvWVctRFRvdzBiRG5KZDFBQTRzZkNoQmJqZXJtcXQ2UV9aYTQiLCJmYW1pbHlfbmFtZSI6IlJhbmRhbGwiLCJnaXZlbl9uYW1lIjoiUmljaCJ9.foobar',
            None
          ],
        ]

        OAuth2Client._crack_jwt

        for testCase in testData:
            testJWT = testCase[0]
            testResult = testCase[1]

            if testResult:
                crackedJwt = OAuth2Client._crack_jwt(testJWT)
                resp = util.dicts_equal(testResult, crackedJwt)
                self.assertTrue(resp is None, 'The cracked token does not match the expected result.: {}'.format(resp))
            else:
                with self.assertRaises(ValueError):
                    crackedJwt = OAuth2Client._crack_jwt(testJWT)



    @httpretty.activate
    def test_bad_int_in_response(self):
        util.setup_expected_user_realm_response_common(False)
        response = util.create_response()

        response['wireResponse']['expires_in'] = 'foo'

        upRequest = self.setup_expected_username_password_request_response(200, response['wireResponse'], response['authority'])
        authorityUrl = response['authority'] + '/' + cp['tenant']
        context = adal.AuthenticationContext(authorityUrl)

        # Did not receive expected error about bad int parameter
        with self.assertRaises(Exception):
            token_response = context.acquire_token_with_username_password(response['resource'], user_pass_params['username'], user_pass_params['password'], client_cred_params['clientId'])

    @unittest.skip('https://github.com/AzureAD/azure-activedirectory-library-for-python-priv/issues/21')
    @httpretty.activate
    def test_bad_id_token_base64_in_response(self):
        foundWarning = False
        util.setup_expected_user_realm_response_common(False)
        response = util.create_response()

        def findIdTokenWarning(level, message):
            if 'decoded' in message:
                foundWarning = True
        util.turn_on_logging() #, findIdTokenWarning)
        #util.turnOnLogging(None, findIdTokenWarning)

        response['wireResponse']['id_token'] = 'aaaaaaa./+===.aaaaaa'
        authorityUrl = response['authority'] + '/' + cp['tenant']
        upRequest = self.setup_expected_username_password_request_response(200, response['wireResponse'], authorityUrl)

        context = adal.AuthenticationContext(authorityUrl)
        token_response = context.acquire_token_with_username_password(response['resource'], user_pass_params['username'], user_pass_params['password'], client_cred_params['clientId'])

        self.assertTrue(foundWarning, 'Did not see expected warning message about bad id_token base64.')

    @httpretty.activate
    def test_no_token_type(self):
        util.setup_expected_user_realm_response_common(False)
        response = util.create_response()
        authorityUrl = response['authority'] + '/' + cp['tenant']

        del response['wireResponse']['token_type']

        upRequest = self.setup_expected_username_password_request_response(200, response['wireResponse'], response['authority'])
        context = adal.AuthenticationContext(authorityUrl)

        # Did not receive expected error about missing token_type
        with self.assertRaises(Exception):
            token_response = context.acquire_token_with_username_password(response['resource'], user_pass_params['username'], user_pass_params['password'], client_cred_params['clientId'])

    @httpretty.activate
    def test_no_access_token(self):
        util.setup_expected_user_realm_response_common(False)
        response = util.create_response()

        del response['wireResponse']['access_token']

        upRequest = self.setup_expected_username_password_request_response(200, response['wireResponse'], response['authority'])
        authorityUrl = response['authority'] + '/' + cp['tenant']
        context = adal.AuthenticationContext(authorityUrl)
        # Did not receive expected error about missing token_type
        with self.assertRaises(Exception):
            token_response = context.acquire_token_with_username_password(response['resource'], user_pass_params['username'], user_pass_params['password'], client_cred_params['clientId'])

if __name__ == '__main__':
    unittest.main()
