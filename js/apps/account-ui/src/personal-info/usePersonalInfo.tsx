import { useState } from "react";
import { useForm, ErrorOption } from "react-hook-form";
import { TFunction } from "i18next";

import {
  getPersonalInfo,
  getSupportedLocales,
  savePersonalInfo,
} from "../api/methods";
import { UserProfileMetadata, UserRepresentation } from "../api/representations";
import { beerify, debeerify, setUserProfileServerError } from "@keycloak/keycloak-ui-shared";
import { usePromise } from "../utils/usePromise";
import { i18n, TFuncKey } from "../i18n";
import { useAccountAlerts } from "../utils/useAccountAlerts";
import type { Environment } from "../environment";

export function usePersonalInfo(context: Environment, t: TFunction) {
  const [userProfileMetadata, setUserProfileMetadata] =
    useState<UserProfileMetadata>();
  const [supportedLocales, setSupportedLocales] = useState<string[]>([]);
  const form = useForm<UserRepresentation>({ mode: "onChange" });
  const { reset, setValue, setError } = form;
  const { addAlert } = useAccountAlerts();

  usePromise(
    (signal) =>
      Promise.all([
        getPersonalInfo({ signal, context }),
        getSupportedLocales({ signal, context }),
      ]),
    ([personalInfo, locales]) => {
      setUserProfileMetadata(personalInfo.userProfileMetadata);
      setSupportedLocales(locales);
      reset(personalInfo);
      Object.entries(personalInfo.attributes || {}).forEach(([k, v]) =>
        setValue(`attributes[${beerify(k)}]`, v),
      );
    },
  );

  const normalizeAttributes = (user: UserRepresentation) =>
    Object.fromEntries(
      Object.entries(user.attributes || {}).map(([k, v]) => [debeerify(k), v]),
    );

  const maybeUpdateLanguage = async (attributes: Record<string, unknown>) => {
    const locale = attributes["locale"]?.toString();
    if (!locale) return;
    await i18n.changeLanguage(locale, (error) => {
      if (error) {
        console.warn("Error(s) loading locale", locale, error);
      }
    });
  };

  const onSubmit = async (user: UserRepresentation) => {
    try {
      const attributes = normalizeAttributes(user);
      await savePersonalInfo(context, { ...user, attributes });
      await maybeUpdateLanguage(attributes);
      await context.keycloak.updateToken();
      addAlert(t("accountUpdatedMessage"));
    } catch (error) {
      addAlert(t("accountUpdatedError"), "danger");
      setUserProfileServerError(
        { responseData: { errors: error as any } },
        (name: string | number, err: unknown) =>
          setError(name as string, err as ErrorOption),
        ((key: TFuncKey, param?: object) => t(key, param as any)) as TFunction,
      );
    }
  };

  const allFieldsReadOnly = () =>
    userProfileMetadata?.attributes
      ?.every((a) => a.readOnly) ?? false;

  return {
    form,
    onSubmit,
    userProfileMetadata,
    supportedLocales,
    allFieldsReadOnly,
  };
}
