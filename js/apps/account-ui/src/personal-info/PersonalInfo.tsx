import {
  UserProfileFields,
  useEnvironment,
} from "@keycloak/keycloak-ui-shared";
import {
  ActionGroup,
  Alert,
  Button,
  ExpandableSection,
  Form,
  Spinner,
} from "@patternfly/react-core";
import { ExternalLinkSquareAltIcon } from "@patternfly/react-icons";
import { useTranslation } from "react-i18next";

import { Page } from "../components/page/Page";
import { usePersonalInfo } from "../hooks/usePersonalInfo";

export const PersonalInfo = () => {
  const { t } = useTranslation();
  const context = useEnvironment();
  const {
    form,
    onSubmit,
    userProfileMetadata,
    supportedLocales,
    allFieldsReadOnly,
  } = usePersonalInfo(context, t);

  if (!userProfileMetadata) return <Spinner />;

  const {
    updateEmailFeatureEnabled,
    updateEmailActionEnabled,
    isRegistrationEmailAsUsername,
    isEditUserNameAllowed,
    deleteAccountAllowed,
    locale,
  } = context.environment.features;

  const renderEmailUpdateButton = (attribute: any) => {
    const annotations = attribute.annotations ?? {};
    const canUpdateEmail =
      attribute.name === "email" &&
      updateEmailFeatureEnabled &&
      updateEmailActionEnabled &&
      annotations["kc.required.action.supported"] &&
      (!isRegistrationEmailAsUsername || isEditUserNameAllowed);

    if (!canUpdateEmail) return undefined;

    return (
      <Button
        id="update-email-btn"
        variant="link"
        onClick={() => context.keycloak.login({ action: "UPDATE_EMAIL" })}
        icon={<ExternalLinkSquareAltIcon />}
        iconPosition="right"
      >
        {t("updateEmail")}
      </Button>
    );
  };

  return (
    <Page title={t("personalInfo")} description={t("personalInfoDescription")}>
      <Form isHorizontal onSubmit={form.handleSubmit(onSubmit)}>
        <UserProfileFields
          form={form}
          userProfileMetadata={userProfileMetadata}
          supportedLocales={supportedLocales}
          currentLocale={locale}
          t={t as any}
          renderer={renderEmailUpdateButton}
        />

        {!allFieldsReadOnly() && (
          <ActionGroup>
            <Button type="submit" id="save-btn" variant="primary">
              {t("save")}
            </Button>
            <Button id="cancel-btn" variant="link" onClick={() => form.reset()}>
              {t("cancel")}
            </Button>
          </ActionGroup>
        )}

        {deleteAccountAllowed && (
          <ExpandableSection toggleText={t("deleteAccount")}>
            <Alert
              isInline
              title={t("deleteAccount")}
              variant="danger"
              actionLinks={
                <Button
                  id="delete-account-btn"
                  variant="danger"
                  onClick={() =>
                    context.keycloak.login({ action: "delete_account" })
                  }
                >
                  {t("delete")}
                </Button>
              }
            >
              {t("deleteAccountWarning")}
            </Alert>
          </ExpandableSection>
        )}
      </Form>
    </Page>
  );
};
